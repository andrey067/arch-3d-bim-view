"""Pydantic v2 schemas for ConversionJob request/response."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.features.models.models import JobStatus


class JobResponse(BaseModel):
    id: str
    model_file_id: str
    status: JobStatus
    attempts: int
    last_error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    glb_url: str | None = None
    usdz_url: str | None = None

    model_config = {"from_attributes": True}


class JobRetryResponse(BaseModel):
    job_id: str
    status: str = "pending"
