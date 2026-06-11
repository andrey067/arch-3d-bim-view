"""Pydantic v2 schemas for VS-Conversion (ConversionJob) request/response."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.features.models.models import JobStatus


class JobResponse(BaseModel):
    """Response payload for GET /api/v1/jobs/{job_id}."""

    id: uuid.UUID
    model_file_id: uuid.UUID
    status: JobStatus
    attempts: int
    last_error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    glb_url: str | None = None
    thumbnail_url: str | None = None

    model_config = {"from_attributes": True}


class JobRetryResponse(BaseModel):
    """Response payload for POST /api/v1/jobs/{job_id}/retry."""

    job_id: uuid.UUID
    status: str = "pending"
