"""Conversion service — orchestrates the conversion pipeline.

Reads ModelFile and ConversionJob from DB, runs the correct pipeline,
and updates job status. Called by the Celery task.
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.storage.keys import glb_key, thumbnail_key
from app.core.storage.local_disk import LocalDiskStorage
from app.features.conversion.pipelines.common import ConversionError, dispatch
from app.features.conversion.pipelines.thumbnail import render as render_thumbnail
from app.features.models.models import ConversionJob, JobStatus, ModelFile, SourceFormat

logger = logging.getLogger(__name__)


def process_conversion(
    session: Session,
    *,
    job_id: uuid.UUID,
    model_file_id: uuid.UUID,
    project_id: uuid.UUID,
    source_format: SourceFormat,
    original_storage_key: str,
    storage: LocalDiskStorage | None = None,
) -> None:
    """Execute the full conversion pipeline for a model file.

    This is the main entry point called by the Celery task.
    It handles the full lifecycle: mark running → convert → mark ready/failed.

    Args:
        session: Database session.
        job_id: The ConversionJob ID.
        model_file_id: The ModelFile ID.
        project_id: The Project ID.
        source_format: Detected source format.
        original_storage_key: Storage key of the original file.
        storage: Optional storage override (for testing).
    """
    settings = get_settings()
    if storage is None:
        storage = LocalDiskStorage(settings.STORAGE_ROOT)

    # Atomically transition pending → running
    now = time.time()
    updated = _try_start_job(session, job_id)
    if not updated:
        logger.warning("Job %s could not transition to running (already started or state changed)", job_id)
        return

    session.commit()

    # Prepare paths
    with _temp_work_dir(model_file_id) as (work_dir, input_path, output_path):
        try:
            # Read original from storage
            _download_original(storage, original_storage_key, input_path)

            # Run pipeline
            pipeline_fn = dispatch(source_format)
            logger.info("Starting conversion: job=%s format=%s", job_id, source_format.value)
            pipeline_fn(input_path, output_path)

            # Upload GLB to storage
            glb_storage = glb_key(str(project_id), str(model_file_id))
            storage.put(glb_storage, output_path, content_type="model/gltf-binary")

            # Generate and upload thumbnail
            thumb_storage = thumbnail_key(str(project_id), str(model_file_id))
            thumb_path = work_dir / "thumbnail.webp"
            thumb_size = (settings.THUMBNAIL_SIZE_W, settings.THUMBNAIL_SIZE_H)

            try:
                render_thumbnail(output_path, thumb_path, size=thumb_size)
                storage.put(thumb_storage, thumb_path, content_type="image/webp")
                logger.info("Thumbnail generated: job=%s thumb_key=%s", job_id, thumb_storage)
            except ConversionError as exc:
                # Thumbnail failure fails the entire job
                duration_ms = int((time.time() - now) * 1000)
                _fail_job(
                    session, job_id,
                    error_message=f"Thumbnail generation failed: {exc}",
                    duration_ms=duration_ms,
                )
                session.commit()
                logger.error("Thumbnail failed: job=%s error=%s", job_id, exc)
                return

            # Mark job as ready
            duration_ms = int((time.time() - now) * 1000)
            _complete_job(
                session, job_id,
                glb_storage_key=glb_storage,
                thumbnail_storage_key=thumb_storage,
                duration_ms=duration_ms,
            )
            session.commit()

            logger.info(
                "Conversion complete: job=%s duration=%dms glb_key=%s thumb_key=%s",
                job_id, duration_ms, glb_storage, thumb_storage,
            )

        except ConversionError as exc:
            duration_ms = int((time.time() - now) * 1000)
            _fail_job(session, job_id, error_message=str(exc), duration_ms=duration_ms)
            session.commit()
            logger.error("Conversion failed: job=%s stage=%s error=%s", job_id, exc.stage, exc)

        except Exception as exc:
            duration_ms = int((time.time() - now) * 1000)
            _fail_job(session, job_id, error_message=f"Unexpected error: {exc}", duration_ms=duration_ms)
            session.commit()
            logger.exception("Unexpected conversion error: job=%s", job_id)


def _try_start_job(session: Session, job_id: uuid.UUID) -> bool:
    """Attempt to transition a job from pending to running.

    Returns True if the transition succeeded.
    """
    settings = get_settings()
    stmt = (
        select(ConversionJob)
        .where(ConversionJob.id == job_id)
        .where(
            (ConversionJob.status == JobStatus.pending)
            | (
                (ConversionJob.status == JobStatus.failed)
                & (ConversionJob.attempts < settings.MAX_CONVERSION_ATTEMPTS)
            )
        )
    )
    job = session.scalar(stmt)
    if job is None:
        return False

    job.status = JobStatus.running
    job.attempts += 1
    job.started_at = session.execute(select(_now_func())).scalar()
    job.last_error = None
    session.flush()
    return True


def _complete_job(
    session: Session,
    job_id: uuid.UUID,
    *,
    glb_storage_key: str,
    thumbnail_storage_key: str,
    duration_ms: int,
) -> None:
    """Mark a job as ready with the produced GLB and thumbnail storage keys."""
    job = session.get(ConversionJob, job_id)
    if job is None:
        return
    job.status = JobStatus.ready
    job.glb_storage_key = glb_storage_key
    job.thumbnail_storage_key = thumbnail_storage_key
    job.duration_ms = duration_ms
    job.finished_at = session.execute(select(_now_func())).scalar()
    session.flush()


def _fail_job(
    session: Session,
    job_id: uuid.UUID,
    *,
    error_message: str,
    duration_ms: int,
) -> None:
    """Mark a job as failed with an error message."""
    job = session.get(ConversionJob, job_id)
    if job is None:
        return
    job.status = JobStatus.failed
    job.last_error = error_message[:4000]  # Truncate for safety
    job.duration_ms = duration_ms
    job.finished_at = session.execute(select(_now_func())).scalar()
    session.flush()


def _download_original(
    storage: LocalDiskStorage,
    storage_key: str,
    destination: Path,
) -> None:
    """Download the original file from storage to a local temp path."""
    with storage.open_for_read(storage_key) as src:
        destination.write_bytes(src.read() if hasattr(src, 'read') else b'')

    if not destination.exists() or destination.stat().st_size == 0:
        raise ConversionError(
            f"Downloaded original is empty: {storage_key}",
            stage="download",
        )


def _now_func():
    """Return the appropriate now function for the current DB dialect."""
    from sqlalchemy import func
    return func.now()


class _temp_work_dir:
    """Context manager that creates a temporary work directory."""

    def __init__(self, model_file_id: uuid.UUID) -> None:
        self._model_file_id = model_file_id
        self._path: Path | None = None

    def __enter__(self) -> tuple[Path, Path, Path]:
        import tempfile
        self._path = Path(tempfile.mkdtemp(prefix=f"conv_{self._model_file_id}_"))
        input_path = self._path / "input"
        output_path = self._path / "output.glb"
        return self._path, input_path, output_path

    def __exit__(self, *args: object) -> None:
        if self._path and self._path.exists():
            import shutil
            shutil.rmtree(self._path, ignore_errors=True)
