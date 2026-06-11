"""FastAPI routes for VS-Conversion (ConversionJob).

Endpoints:
    GET  /api/v1/jobs/{job_id}        — query job status
    POST /api/v1/jobs/{job_id}/retry  — retry a failed job
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.storage.keys import glb_key
from app.features.auth.service import get_current_user
from app.features.conversion.schemas import JobResponse, JobRetryResponse
from app.features.conversion.tasks import process_model_file
from app.features.models.models import ConversionJob, JobStatus, ModelFile
from app.features.projects import persistence as projects_persistence

router = APIRouter(tags=["jobs"])


def _get_user(authorization: str, db: Session):
    """Extract and validate the current user from the Authorization header."""
    from app.core.errors import UnauthorizedError

    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header.")
    token = authorization.removeprefix("Bearer ").strip()
    return get_current_user(db, token=token)


def _verify_job_ownership(db: Session, job: ConversionJob, user_id: uuid.UUID) -> None:
    """Verify the user owns the project that contains the job's model file."""
    model_file = db.get(ModelFile, job.model_file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    project = projects_persistence.get_project_by_id(db, model_file.project_id)
    if project is None or project.owner_id != user_id:
        raise ForbiddenError("You do not have access to this job.")


@router.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobResponse,
)
def get_job_status(
    job_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> JobResponse:
    """Get the status and metadata of a conversion job.

    Only the project owner can query job status.
    Returns GLB/thumbnail URLs only when status is 'ready'.
    """
    user = _get_user(authorization, db)

    job = db.get(ConversionJob, job_id)
    if job is None:
        raise NotFoundError("Conversion job not found.")

    _verify_job_ownership(db, job, user.id)

    # Build URLs only when job is ready
    glb_url = None
    thumbnail_url = None
    if job.status == JobStatus.ready:
        model_file = db.get(ModelFile, job.model_file_id)
        if model_file and job.glb_storage_key:
            glb_url = f"/api/v1/files/{model_file.id}/glb"
        if model_file and job.thumbnail_storage_key:
            thumbnail_url = f"/api/v1/files/{model_file.id}/thumbnail"

    return JobResponse(
        id=job.id,
        model_file_id=job.model_file_id,
        status=job.status,
        attempts=job.attempts,
        last_error=job.last_error,
        started_at=job.started_at,
        finished_at=job.finished_at,
        duration_ms=job.duration_ms,
        glb_url=glb_url,
        thumbnail_url=thumbnail_url,
    )


@router.post(
    "/api/v1/jobs/{job_id}/retry",
    response_model=JobRetryResponse,
    status_code=202,
)
def retry_job(
    job_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> JobRetryResponse:
    """Retry a failed conversion job.

    Resets the existing job to 'pending' and enqueues it again.
    Returns 409 if the current job is not in 'failed' status.
    """
    user = _get_user(authorization, db)

    job = db.get(ConversionJob, job_id)
    if job is None:
        raise NotFoundError("Conversion job not found.")

    _verify_job_ownership(db, job, user.id)

    if job.status != JobStatus.failed:
        raise ConflictError(
            f"Cannot retry job in '{job.status.value}' status. "
            "Only failed jobs can be retried."
        )

    model_file = db.get(ModelFile, job.model_file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    # Reset the existing job to pending
    job.status = JobStatus.pending
    job.last_error = None
    job.started_at = None
    job.finished_at = None
    job.duration_ms = None
    job.glb_storage_key = None
    db.flush()

    # Enqueue the conversion task (best-effort)
    import logging
    logger = logging.getLogger(__name__)

    try:
        process_model_file.delay(
            job_id=str(job.id),
            model_file_id=str(model_file.id),
            project_id=str(model_file.project_id),
            source_format=model_file.source_format.value,
            original_storage_key=model_file.original_storage_key,
        )
    except Exception as exc:
        logger.warning("Failed to enqueue conversion task for retry: %s", exc)

    db.commit()

    return JobRetryResponse(job_id=job.id)
