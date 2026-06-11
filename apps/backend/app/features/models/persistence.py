"""Database queries for VS-Upload (ModelFile)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.models.models import ModelFile, SourceFormat


def create_model_file(
    session: Session,
    *,
    project_id: uuid.UUID,
    uploader_id: uuid.UUID,
    original_filename: str,
    source_format: SourceFormat,
    size_bytes: int,
    original_storage_key: str,
    content_hash: str,
) -> ModelFile:
    model_file = ModelFile(
        project_id=project_id,
        uploader_id=uploader_id,
        original_filename=original_filename,
        source_format=source_format,
        size_bytes=size_bytes,
        original_storage_key=original_storage_key,
        content_hash=content_hash,
    )
    session.add(model_file)
    session.flush()
    return model_file


def get_model_file_by_id(session: Session, model_file_id: uuid.UUID) -> ModelFile | None:
    return session.get(ModelFile, model_file_id)


def list_model_files(
    session: Session,
    *,
    project_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = 20,
) -> list[ModelFile]:
    stmt = select(ModelFile).where(ModelFile.project_id == project_id)
    if cursor:
        try:
            cursor_dt = uuid.UUID(cursor)
        except ValueError:
            cursor_dt = None
        if cursor_dt:
            stmt = stmt.where(ModelFile.id > cursor_dt)
    stmt = stmt.order_by(ModelFile.uploaded_at.desc()).limit(limit + 1)
    return list(session.scalars(stmt).all())


def delete_model_file(session: Session, model_file: ModelFile) -> None:
    session.delete(model_file)
    session.flush()
