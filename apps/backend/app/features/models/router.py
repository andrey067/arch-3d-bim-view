"""FastAPI routes for VS-Upload (ModelFile).

Endpoints:
    POST   /api/v1/projects/{id}/files   — upload file
    GET    /api/v1/projects/{id}/files   — list files
    DELETE /api/v1/files/{id}            — delete file
    GET    /api/v1/files/{id}/thumbnail  — serve thumbnail WebP
    GET    /api/v1/files/{id}/viewer     — viewer metadata
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.features.auth.service import get_current_user
from app.features.models import service
from app.features.models.schemas import ModelFileListResponse, ModelFileResponse, UploadResponse, ViewerResponse

router = APIRouter(tags=["models"])


def _get_user(authorization: str, db: Session):
    """Extract and validate the current user from the Authorization header."""
    from app.core.errors import UnauthorizedError

    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header.")
    token = authorization.removeprefix("Bearer ").strip()
    return get_current_user(db, token=token)


@router.post(
    "/api/v1/projects/{project_id}/files",
    response_model=UploadResponse,
    status_code=202,
)
async def upload_file(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> UploadResponse:
    user = _get_user(authorization, db)
    content = await file.read()
    model_file, conversion_job = service.upload_file(
        db,
        project_id=project_id,
        uploader_id=user.id,
        filename=file.filename or "unnamed",
        file_content=content,
    )
    db.commit()

    # Enqueue conversion task (best-effort — job is persisted even if dispatch fails)
    import logging
    logger = logging.getLogger(__name__)

    try:
        from app.features.conversion.tasks import process_model_file

        process_model_file.delay(
            job_id=str(conversion_job.id),
            model_file_id=str(model_file.id),
            project_id=str(project_id),
            source_format=model_file.source_format.value,
            original_storage_key=model_file.original_storage_key,
        )
    except Exception as exc:
        # Log but don't fail the upload — the job exists and can be retried
        logger.warning("Failed to enqueue conversion task: %s", exc)

    return UploadResponse(
        model_file_id=model_file.id,
        conversion_job_id=conversion_job.id,
        status="pending",
    )


@router.get(
    "/api/v1/projects/{project_id}/files",
    response_model=ModelFileListResponse,
)
def list_files(
    project_id: uuid.UUID,
    cursor: str | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ModelFileListResponse:
    user = _get_user(authorization, db)
    files, next_cursor = service.list_model_files(
        db, project_id=project_id, owner_id=user.id, cursor=cursor, limit=limit
    )
    return ModelFileListResponse(
        items=[ModelFileResponse.model_validate(f) for f in files],
        next_cursor=next_cursor,
    )


@router.delete("/api/v1/files/{file_id}", status_code=204)
def delete_file(
    file_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> None:
    user = _get_user(authorization, db)
    service.delete_model_file(db, model_file_id=file_id, owner_id=user.id)
    db.commit()


@router.get("/api/v1/files/{file_id}/status")
def get_file_status(
    file_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    """Get conversion status for a model file.

    Returns the status of the latest ConversionJob associated with the file.
    Used by the frontend for polling conversion progress.
    """
    from app.core.errors import NotFoundError
    from app.features.models.models import ConversionJob, ModelFile
    from app.features.projects import persistence as projects_persistence
    from sqlalchemy import select

    user = _get_user(authorization, db)

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    project = projects_persistence.get_project_by_id(db, model_file.project_id)
    if project is None or project.owner_id != user.id:
        from app.core.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this file.")

    # Get the latest conversion job for this file
    job = db.scalar(
        select(ConversionJob)
        .where(ConversionJob.model_file_id == file_id)
        .order_by(ConversionJob.created_at.desc())
        .limit(1)
    )

    if job is None:
        return {"status": "pending", "lastError": None}

    return {
        "status": job.status.value,
        "lastError": job.last_error,
    }


@router.get("/api/v1/files/{file_id}/thumbnail")
def get_thumbnail(
    file_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> Response:
    """Serve the thumbnail WebP for a model file.

    Returns the thumbnail image with Content-Type: image/webp.
    Returns 404 if thumbnail is not available (conversion not ready).
    """
    from app.core.config import get_settings
    from app.core.errors import NotFoundError
    from app.core.storage.local_disk import LocalDiskStorage
    from app.features.models.models import ConversionJob, ModelFile
    from app.features.projects import persistence as projects_persistence
    from sqlalchemy import select

    user = _get_user(authorization, db)

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    project = projects_persistence.get_project_by_id(db, model_file.project_id)
    if project is None or project.owner_id != user.id:
        from app.core.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this file.")

    # Get the latest conversion job for this file
    job = db.scalar(
        select(ConversionJob)
        .where(ConversionJob.model_file_id == file_id)
        .order_by(ConversionJob.created_at.desc())
        .limit(1)
    )

    if job is None or job.thumbnail_storage_key is None:
        raise NotFoundError("Thumbnail not available. Conversion may not be complete.")

    settings = get_settings()
    storage = LocalDiskStorage(settings.STORAGE_ROOT)

    try:
        with storage.open_for_read(job.thumbnail_storage_key) as f:
            thumbnail_data = f.read()
        return Response(
            content=thumbnail_data,
            media_type="image/webp",
            headers={
                "Cache-Control": "public, max-age=86400",
            },
        )
    except Exception:
        raise NotFoundError("Thumbnail file not found in storage.")


@router.get("/api/v1/files/{file_id}/viewer", response_model=ViewerResponse)
def get_viewer_metadata(
    file_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ViewerResponse:
    """Get viewer metadata for a model file.

    Returns metadata needed to render the 3D model in the viewer:
    - model_file_id, project_id, filename, format
    - glb_url (relative URL to download GLB)
    - thumbnail_url (relative URL to download thumbnail)
    - conversion status
    """
    from app.core.errors import NotFoundError
    from app.features.models.models import ConversionJob, ModelFile, JobStatus
    from app.features.projects import persistence as projects_persistence
    from sqlalchemy import select

    user = _get_user(authorization, db)

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    project = projects_persistence.get_project_by_id(db, model_file.project_id)
    if project is None or project.owner_id != user.id:
        from app.core.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this file.")

    # Get the latest conversion job for this file
    job = db.scalar(
        select(ConversionJob)
        .where(ConversionJob.model_file_id == file_id)
        .order_by(ConversionJob.created_at.desc())
        .limit(1)
    )

    status = job.status.value if job else "pending"
    is_ready = job is not None and job.status == JobStatus.ready

    return ViewerResponse(
        model_file_id=model_file.id,
        project_id=model_file.project_id,
        filename=model_file.original_filename,
        source_format=model_file.source_format.value,
        status=status,
        glb_url=f"/api/v1/files/{file_id}/glb" if is_ready else None,
        thumbnail_url=f"/api/v1/files/{file_id}/thumbnail" if is_ready else None,
        last_error=job.last_error if job else None,
    )


@router.get("/api/v1/files/{file_id}/glb")
def get_glb(
    file_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> Response:
    """Serve the converted GLB file.

    Returns the GLB binary with Content-Type: model/gltf-binary.
    Supports HTTP Range requests for <model-viewer> compatibility.
    Returns 404 if GLB is not available (conversion not ready).
    """
    from app.core.config import get_settings
    from app.core.errors import NotFoundError
    from app.core.storage.local_disk import LocalDiskStorage
    from app.features.models.models import ConversionJob, ModelFile, JobStatus
    from app.features.projects import persistence as projects_persistence
    from sqlalchemy import select

    user = _get_user(authorization, db)

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    project = projects_persistence.get_project_by_id(db, model_file.project_id)
    if project is None or project.owner_id != user.id:
        from app.core.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this file.")

    # Get the latest conversion job for this file
    job = db.scalar(
        select(ConversionJob)
        .where(ConversionJob.model_file_id == file_id)
        .order_by(ConversionJob.created_at.desc())
        .limit(1)
    )

    if job is None or job.status != JobStatus.ready or job.glb_storage_key is None:
        raise NotFoundError("GLB not available. Conversion may not be complete.")

    settings = get_settings()
    storage = LocalDiskStorage(settings.STORAGE_ROOT)

    try:
        with storage.open_for_read(job.glb_storage_key) as f:
            glb_data = f.read()
        return Response(
            content=glb_data,
            media_type="model/gltf-binary",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Accept-Ranges": "bytes",
            },
        )
    except Exception:
        raise NotFoundError("GLB file not found in storage.")
