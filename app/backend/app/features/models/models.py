"""ModelFile + ConversionJob entities.

Simplified for SQLite: UUIDs stored as strings, no postgres-specific types.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SourceFormat(str, enum.Enum):
    ifc = "ifc"
    dae = "dae"
    obj = "obj"
    glb = "glb"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    ready = "ready"
    failed = "failed"


def _uuid_str() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelFile(Base):
    __tablename__ = "model_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    uploader_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_format: Mapped[SourceFormat] = mapped_column(
        Enum(SourceFormat, name="source_format_enum"),
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    def __repr__(self) -> str:
        return f"<ModelFile {self.original_filename!r}>"


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    model_file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("model_files.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"),
        nullable=False,
        default=JobStatus.pending,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_utcnow)
    glb_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    usdz_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    qr_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<ConversionJob {self.status.value}>"
