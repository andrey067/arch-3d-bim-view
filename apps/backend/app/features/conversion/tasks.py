"""Celery tasks for the conversion pipeline.

Defines the `process_model_file` task that is enqueued after upload.
"""
from __future__ import annotations

import uuid

from app.features.conversion.worker import celery_app


@celery_app.task(
    name="conversion.process_model_file",
    bind=True,
    max_retries=0,  # Manual retry only via API
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_model_file(
    self,
    job_id: str,
    model_file_id: str,
    project_id: str,
    source_format: str,
    original_storage_key: str,
) -> dict[str, str]:
    """Process a model file conversion.

    This task is enqueued by the upload endpoint. It:
    1. Transitions the ConversionJob from pending to running
    2. Downloads the original file from storage
    3. Runs the format-specific pipeline (IFC→IfcOpenShell→Blender, DAE/OBJ/GLB→Blender)
    4. Uploads the GLB to converted storage
    5. Transitions the job to ready (or failed on error)

    Args:
        job_id: UUID string of the ConversionJob.
        model_file_id: UUID string of the ModelFile.
        project_id: UUID string of the Project.
        source_format: One of 'ifc', 'dae', 'obj', 'glb'.
        original_storage_key: Storage key of the uploaded original.

    Returns:
        Dict with status and job_id for monitoring.
    """
    from app.core.db import SessionLocal
    from app.features.conversion.service import process_conversion
    from app.features.models.models import SourceFormat

    fmt = SourceFormat(source_format)
    session = SessionLocal()

    try:
        process_conversion(
            session,
            job_id=uuid.UUID(job_id),
            model_file_id=uuid.UUID(model_file_id),
            project_id=uuid.UUID(project_id),
            source_format=fmt,
            original_storage_key=original_storage_key,
        )
        return {"status": "ok", "job_id": job_id}
    except Exception:
        # If service didn't handle the error, fail gracefully
        session.rollback()
        raise
    finally:
        session.close()
