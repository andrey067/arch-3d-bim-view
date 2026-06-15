"""FastAPI routes for ModelFile upload and management.

Simplified: uses BackgroundTasks instead of Celery for conversion.
Open access — no auth required.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.db import get_db, SessionLocal
from app.core.identity import DEFAULT_OWNER_ID
from app.features.models import service
from app.features.models.schemas import ModelFileListResponse, ModelFileResponse, UploadResponse, ViewerResponse

router = APIRouter(tags=["models"])


@router.post(
    "/api/v1/projects/{project_id}/files",
    response_model=UploadResponse,
    status_code=202,
)
async def upload_file(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    content = await file.read()
    model_file, conversion_job = service.upload_file(
        db,
        project_id=project_id,
        uploader_id=DEFAULT_OWNER_ID,
        filename=file.filename or "unnamed",
        file_content=content,
    )
    db.commit()

    from app.features.conversion.service import process_conversion
    background_tasks.add_task(
        process_conversion,
        session_factory=SessionLocal,
        job_id=str(conversion_job.id),
        model_file_id=str(model_file.id),
        project_id=str(project_id),
        source_format=model_file.source_format.value,
        original_storage_key=model_file.original_storage_key,
    )

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
    project_id: str,
    cursor: str | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> ModelFileListResponse:
    files, next_cursor = service.list_model_files(
        db, project_id=project_id, owner_id=DEFAULT_OWNER_ID, cursor=cursor, limit=limit,
    )
    return ModelFileListResponse(
        items=[ModelFileResponse.model_validate(f) for f in files],
        next_cursor=next_cursor,
    )


@router.delete("/api/v1/files/{file_id}", status_code=204)
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
) -> None:
    service.delete_model_file(db, model_file_id=file_id, owner_id=DEFAULT_OWNER_ID)
    db.commit()


@router.get("/api/v1/files/{file_id}/status")
def get_file_status(
    file_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    from app.core.errors import NotFoundError
    from app.features.models.models import ConversionJob, ModelFile
    from sqlalchemy import select

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

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


@router.get("/api/v1/files/{file_id}/viewer", response_model=ViewerResponse)
def get_viewer_metadata(
    file_id: str,
    db: Session = Depends(get_db),
) -> ViewerResponse:
    from app.core.errors import NotFoundError
    from app.features.models.models import ConversionJob, ModelFile, JobStatus
    from sqlalchemy import select

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

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
        usdz_url=f"/api/v1/files/{file_id}/usdz" if is_ready and job.usdz_storage_key else None,
        qr_url=f"/api/v1/files/{file_id}/qr" if is_ready and job.qr_storage_key else None,
        last_error=job.last_error if job else None,
    )


@router.get("/api/v1/files/{file_id}/glb")
def get_glb(
    file_id: str,
    db: Session = Depends(get_db),
) -> Response:
    from app.core.config import get_settings
    from app.core.errors import NotFoundError
    from app.core.storage.local_disk import LocalDiskStorage
    from app.features.models.models import ConversionJob, ModelFile, JobStatus
    from sqlalchemy import select

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

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


@router.get("/api/v1/files/{file_id}/usdz")
def get_usdz(
    file_id: str,
    db: Session = Depends(get_db),
) -> Response:
    from app.core.config import get_settings
    from app.core.errors import NotFoundError
    from app.core.storage.local_disk import LocalDiskStorage
    from app.features.models.models import ConversionJob, ModelFile, JobStatus
    from sqlalchemy import select

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    job = db.scalar(
        select(ConversionJob)
        .where(ConversionJob.model_file_id == file_id)
        .order_by(ConversionJob.created_at.desc())
        .limit(1)
    )

    if job is None or job.status != JobStatus.ready or job.usdz_storage_key is None:
        raise NotFoundError("USDZ not available.")

    settings = get_settings()
    storage = LocalDiskStorage(settings.STORAGE_ROOT)

    try:
        with storage.open_for_read(job.usdz_storage_key) as f:
            usdz_data = f.read()
        return Response(
            content=usdz_data,
            media_type="model/usd",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception:
        raise NotFoundError("USDZ file not found in storage.")


@router.get("/api/v1/files/{file_id}/qr")
def get_qr(
    file_id: str,
    db: Session = Depends(get_db),
) -> Response:
    from app.core.config import get_settings
    from app.core.errors import NotFoundError
    from app.core.storage.local_disk import LocalDiskStorage
    from app.features.models.models import ConversionJob, ModelFile, JobStatus
    from sqlalchemy import select

    model_file = db.get(ModelFile, file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    job = db.scalar(
        select(ConversionJob)
        .where(ConversionJob.model_file_id == file_id)
        .order_by(ConversionJob.created_at.desc())
        .limit(1)
    )

    if job is None or job.qr_storage_key is None:
        raise NotFoundError("QR code not available.")

    settings = get_settings()
    storage = LocalDiskStorage(settings.STORAGE_ROOT)

    try:
        with storage.open_for_read(job.qr_storage_key) as f:
            qr_data = f.read()
        return Response(
            content=qr_data,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception:
        raise NotFoundError("QR file not found in storage.")
