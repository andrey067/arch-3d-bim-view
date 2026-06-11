"""Business logic for VS-Upload (ModelFile).

Orchestrates file upload validation, storage, and DB persistence.
All persistence concerns are delegated to persistence.py.
"""
from __future__ import annotations

import hashlib
import uuid
from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from app.core.storage.keys import original_key
from app.core.storage.local_disk import LocalDiskStorage
from app.features.models import persistence
from app.features.models.detection import detect_format, get_extension, is_rejected_format
from app.features.models.models import ModelFile, SourceFormat
from app.features.projects import persistence as projects_persistence

# Allowed extensions mapping
ALLOWED_EXTENSIONS: dict[str, SourceFormat] = {
    "ifc": SourceFormat.ifc,
    "dae": SourceFormat.dae,
    "obj": SourceFormat.obj,
    "glb": SourceFormat.glb,
}

REJECTED_EXTENSIONS = {"stl", "rvt", "dwg", "dxf", "skp"}


def _compute_hash(data: bytes) -> str:
    """Compute SHA-256 hex digest of file content."""
    return hashlib.sha256(data).hexdigest()


def upload_file(
    session: Session,
    *,
    project_id: uuid.UUID,
    uploader_id: uuid.UUID,
    filename: str,
    file_content: bytes,
    storage: LocalDiskStorage | None = None,
) -> tuple[ModelFile, "ConversionJob"]:
    """Validate, detect format, store, and persist a model file.

    Also creates a ConversionJob in 'pending' status for the uploaded file.

    Args:
        session: Database session.
        project_id: Target project.
        uploader_id: User uploading the file.
        filename: Original filename.
        file_content: Raw file bytes.
        storage: Optional storage override (for testing).

    Returns:
        Tuple of (ModelFile, ConversionJob).

    Raises:
        NotFoundError: Project not found.
        ForbiddenError: Not the project owner.
        ConflictError: Project is archived.
        UnsupportedMediaTypeError: Format not supported.
        ValidationError: File too large or invalid.
    """
    settings = get_settings()

    # Validate project exists and user has access
    project = projects_persistence.get_project_by_id(session, project_id)
    if not project:
        raise NotFoundError("Project not found.")
    if project.owner_id != uploader_id:
        raise ForbiddenError("You do not have access to this project.")
    if project.archived_at:
        raise ConflictError("Cannot upload to an archived project.")

    # Validate file size
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(file_content) > max_bytes:
        raise ValidationError(f"File exceeds maximum size of {settings.MAX_UPLOAD_MB} MB.")
    if len(file_content) == 0:
        raise ValidationError("File is empty.")

    # Check extension for rejected formats
    ext = get_extension(filename)
    if ext and ext in REJECTED_EXTENSIONS:
        raise UnsupportedMediaTypeError(
            f"Format '{ext}' is not supported. Supported formats: IFC, DAE, OBJ, GLB."
        )

    # Detect format by magic bytes
    headers = file_content[:512]
    source_format = detect_format(headers)

    # Check for rejected format by magic bytes
    if source_format is None and is_rejected_format(headers):
        raise UnsupportedMediaTypeError(
            "File format is not supported. Supported formats: IFC, DAE, OBJ, GLB."
        )

    # Fallback: try extension-based detection
    if source_format is None and ext:
        source_format = ALLOWED_EXTENSIONS.get(ext)

    if source_format is None:
        raise UnsupportedMediaTypeError(
            "Could not detect file format. Supported formats: IFC, DAE, OBJ, GLB."
        )

    # Verify extension matches detected format
    if ext and ext in ALLOWED_EXTENSIONS and ALLOWED_EXTENSIONS[ext] != source_format:
        raise UnsupportedMediaTypeError(
            f"File extension '.{ext}' does not match detected format '{source_format.value}'."
        )

    # Compute content hash
    content_hash = _compute_hash(file_content)

    # Generate storage key
    model_file_id = uuid.uuid4()
    storage_key = original_key(str(project_id), str(model_file_id), filename)

    # Store file
    if storage is None:
        storage = LocalDiskStorage(settings.STORAGE_ROOT)
    storage.put(storage_key, BytesIO(file_content), content_type="application/octet-stream")

    # Persist to DB
    model_file = persistence.create_model_file(
        session,
        project_id=project_id,
        uploader_id=uploader_id,
        original_filename=filename,
        source_format=source_format,
        size_bytes=len(file_content),
        original_storage_key=storage_key,
        content_hash=content_hash,
    )

    # Create ConversionJob in pending status
    from app.features.models.models import ConversionJob, JobStatus

    conversion_job = ConversionJob(
        model_file_id=model_file.id,
        status=JobStatus.pending,
        attempts=0,
    )
    session.add(conversion_job)
    session.flush()

    return model_file, conversion_job


def get_model_file(
    session: Session,
    *,
    model_file_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> ModelFile:
    """Get a model file by ID, verifying ownership."""
    model_file = persistence.get_model_file_by_id(session, model_file_id)
    if not model_file:
        raise NotFoundError("Model file not found.")

    # Verify ownership through project
    project = projects_persistence.get_project_by_id(session, model_file.project_id)
    if not project or project.owner_id != owner_id:
        raise ForbiddenError("You do not have access to this model file.")

    return model_file


def list_model_files(
    session: Session,
    *,
    project_id: uuid.UUID,
    owner_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[list[ModelFile], str | None]:
    """List model files for a project, verifying ownership."""
    project = projects_persistence.get_project_by_id(session, project_id)
    if not project:
        raise NotFoundError("Project not found.")
    if project.owner_id != owner_id:
        raise ForbiddenError("You do not have access to this project.")

    files = persistence.list_model_files(session, project_id=project_id, cursor=cursor, limit=limit)
    has_more = len(files) > limit
    if has_more:
        files = files[:limit]
    next_cursor = str(files[-1].id) if has_more and files else None

    return files, next_cursor


def delete_model_file(
    session: Session,
    *,
    model_file_id: uuid.UUID,
    owner_id: uuid.UUID,
    storage: LocalDiskStorage | None = None,
) -> None:
    """Delete a model file, its storage, and associated conversion job."""
    model_file = get_model_file(session, model_file_id=model_file_id, owner_id=owner_id)

    if storage is None:
        settings = get_settings()
        storage = LocalDiskStorage(settings.STORAGE_ROOT)

    # Delete from storage (best-effort)
    try:
        storage.delete(model_file.original_storage_key)
    except Exception:
        pass

    # Delete associated conversion job and its storage
    from app.features.models.models import ConversionJob
    from sqlalchemy import select

    job = session.scalar(
        select(ConversionJob).where(ConversionJob.model_file_id == model_file_id)
    )
    if job:
        if job.glb_storage_key:
            try:
                storage.delete(job.glb_storage_key)
            except Exception:
                pass
        if job.thumbnail_storage_key:
            try:
                storage.delete(job.thumbnail_storage_key)
            except Exception:
                pass
        session.delete(job)

    persistence.delete_model_file(session, model_file)
