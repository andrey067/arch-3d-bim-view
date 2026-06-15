"""FastAPI routes for ConversionJob — open access (no auth)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db, SessionLocal
from app.core.errors import ConflictError, NotFoundError
from app.features.conversion.schemas import JobResponse, JobRetryResponse
from app.features.models.models import ConversionJob, JobStatus, ModelFile

router = APIRouter(tags=["jobs"])


@router.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobResponse,
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
) -> JobResponse:
    job = db.get(ConversionJob, job_id)
    if job is None:
        raise NotFoundError("Conversion job not found.")

    glb_url = None
    usdz_url = None
    if job.status == JobStatus.ready:
        model_file = db.get(ModelFile, job.model_file_id)
        if model_file and job.glb_storage_key:
            glb_url = f"/api/v1/files/{model_file.id}/glb"
        if model_file and job.usdz_storage_key:
            usdz_url = f"/api/v1/files/{model_file.id}/usdz"

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
        usdz_url=usdz_url,
    )


@router.post(
    "/api/v1/jobs/{job_id}/retry",
    response_model=JobRetryResponse,
    status_code=202,
)
def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobRetryResponse:
    job = db.get(ConversionJob, job_id)
    if job is None:
        raise NotFoundError("Conversion job not found.")

    if job.status != JobStatus.failed:
        raise ConflictError(
            f"Cannot retry job in '{job.status.value}' status. "
            "Only failed jobs can be retried."
        )

    model_file = db.get(ModelFile, job.model_file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    job.status = JobStatus.pending
    job.last_error = None
    job.started_at = None
    job.finished_at = None
    job.duration_ms = None
    job.glb_storage_key = None
    job.usdz_storage_key = None
    job.qr_storage_key = None
    db.commit()

    from app.features.conversion.service import process_conversion
    background_tasks.add_task(
        process_conversion,
        session_factory=SessionLocal,
        job_id=str(job.id),
        model_file_id=str(model_file.id),
        project_id=str(model_file.project_id),
        source_format=model_file.source_format.value,
        original_storage_key=model_file.original_storage_key,
    )

    return JobRetryResponse(job_id=job.id)
