"""Conversion service — orchestrates the conversion pipeline.

Simplified MVP: uses FastAPI BackgroundTasks instead of Celery.
Reads ModelFile and ConversionJob from DB, runs the correct pipeline,
and updates job status.
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.storage.keys import glb_key, usdz_key, qr_key
from app.core.storage.local_disk import LocalDiskStorage
from app.features.conversion.pipelines.common import ConversionError, dispatch
from app.features.conversion.pipelines.usdz import run as convert_usdz
from app.features.conversion.pipelines.qr import generate_qr
from app.features.models.models import ConversionJob, JobStatus, ModelFile, SourceFormat

logger = logging.getLogger(__name__)


def process_conversion(
    session_factory,
    *,
    job_id: str,
    model_file_id: str,
    project_id: str,
    source_format: str,
    original_storage_key: str,
    share_url: str | None = None,
) -> None:
    """Execute the full conversion pipeline for a model file.

    Called as a background task. Creates its own DB session.

    Args:
        session_factory: Callable that returns a new Session.
        job_id: The ConversionJob ID.
        model_file_id: The ModelFile ID.
        project_id: The Project ID.
        source_format: Detected source format.
        original_storage_key: Storage key of the original file.
        share_url: Optional URL for QR code generation.
    """
    settings = get_settings()
    storage = LocalDiskStorage(settings.STORAGE_ROOT)
    session = session_factory()

    # Atomically transition pending → running
    now = time.time()
    updated = _try_start_job(session, job_id)
    if not updated:
        logger.warning("Job %s could not transition to running", job_id)
        session.close()
        return

    session.commit()

    # Prepare paths
    work_dir = Path(f"/tmp/conv_{model_file_id}")
    work_dir.mkdir(parents=True, exist_ok=True)
    # Keep the real extension so trimesh/IfcConvert can detect the format.
    fmt_ext = source_format.value if hasattr(source_format, "value") else str(source_format)
    input_path = work_dir / f"input.{fmt_ext}"
    output_glb_path = work_dir / "output.glb"

    try:
        # Read original from storage
        _download_original(storage, original_storage_key, input_path)

        # Run GLB conversion
        pipeline_fn = dispatch(source_format)
        logger.info("Starting conversion: job=%s format=%s", job_id, source_format)
        pipeline_fn(input_path, output_glb_path)

        # Upload GLB to storage
        glb_storage = glb_key(project_id, model_file_id)
        storage.put(glb_storage, output_glb_path, content_type="model/gltf-binary")

        # Generate USDZ (best effort — only if usd_from_gltf is available)
        usdz_storage: str | None = None
        try:
            output_usdz_path = work_dir / "output.usdz"
            convert_usdz(output_glb_path, output_usdz_path)
            usdz_storage = usdz_key(project_id, model_file_id)
            storage.put(usdz_storage, output_usdz_path, content_type="model/usd")
            logger.info("USDZ generated: job=%s", job_id)
        except ConversionError as exc:
            logger.warning("USDZ skipped (usd_from_gltf unavailable): %s", exc)

        # Generate QR code (best effort)
        qr_storage: str | None = None
        if share_url:
            try:
                qr_path = work_dir / "qr.png"
                generate_qr(share_url, qr_path)
                qr_storage = qr_key(project_id, model_file_id)
                storage.put(qr_storage, qr_path, content_type="image/png")
                logger.info("QR generated: job=%s", job_id)
            except ConversionError as exc:
                logger.warning("QR generation failed: %s", exc)

        # Mark job as ready
        duration_ms = int((time.time() - now) * 1000)
        _complete_job(
            session, job_id,
            glb_storage_key=glb_storage,
            usdz_storage_key=usdz_storage,
            qr_storage_key=qr_storage,
            duration_ms=duration_ms,
        )
        session.commit()

        logger.info(
            "Conversion complete: job=%s duration=%dms glb=%s usdz=%s qr=%s",
            job_id, duration_ms, glb_storage, usdz_storage, qr_storage,
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

    finally:
        # Cleanup temp dir
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)
        session.close()


def _try_start_job(session: Session, job_id: str) -> bool:
    """Attempt to transition a job from pending to running."""
    stmt = (
        select(ConversionJob)
        .where(ConversionJob.id == job_id)
        .where(
            (ConversionJob.status == JobStatus.pending)
            | (
                (ConversionJob.status == JobStatus.failed)
                & (ConversionJob.attempts < get_settings().MAX_CONVERSION_ATTEMPTS)
            )
        )
    )
    job = session.scalar(stmt)
    if job is None:
        return False

    from datetime import datetime, timezone
    job.status = JobStatus.running
    job.attempts += 1
    job.started_at = datetime.now(timezone.utc)
    job.last_error = None
    session.flush()
    return True


def _complete_job(
    session: Session,
    job_id: str,
    *,
    glb_storage_key: str,
    usdz_storage_key: str | None,
    qr_storage_key: str | None,
    duration_ms: int,
) -> None:
    """Mark a job as ready with produced storage keys."""
    from datetime import datetime, timezone
    job = session.get(ConversionJob, job_id)
    if job is None:
        return
    job.status = JobStatus.ready
    job.glb_storage_key = glb_storage_key
    job.usdz_storage_key = usdz_storage_key
    job.qr_storage_key = qr_storage_key
    job.duration_ms = duration_ms
    job.finished_at = datetime.now(timezone.utc)
    session.flush()


def _fail_job(
    session: Session,
    job_id: str,
    *,
    error_message: str,
    duration_ms: int,
) -> None:
    """Mark a job as failed with an error message."""
    from datetime import datetime, timezone
    job = session.get(ConversionJob, job_id)
    if job is None:
        return
    job.status = JobStatus.failed
    job.last_error = error_message[:4000]
    job.duration_ms = duration_ms
    job.finished_at = datetime.now(timezone.utc)
    session.flush()


def _download_original(
    storage: LocalDiskStorage,
    storage_key: str,
    destination: Path,
) -> None:
    """Download the original file from storage to a local temp path."""
    with storage.open_for_read(storage_key) as src:
        destination.write_bytes(src.read())

    if not destination.exists() or destination.stat().st_size == 0:
        raise ConversionError(
            f"Downloaded original is empty: {storage_key}",
            stage="download",
        )
