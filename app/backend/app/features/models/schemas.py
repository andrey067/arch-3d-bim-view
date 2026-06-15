"""Pydantic v2 schemas for ModelFile request/response contracts."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.features.models.models import SourceFormat


class ModelFileResponse(BaseModel):
    id: str
    project_id: str
    uploader_id: str
    original_filename: str
    source_format: SourceFormat
    size_bytes: int
    uploaded_at: datetime
    content_hash: str

    model_config = {"from_attributes": True}


class ModelFileListResponse(BaseModel):
    items: list[ModelFileResponse]
    next_cursor: str | None = None


class UploadResponse(BaseModel):
    model_file_id: str
    conversion_job_id: str
    status: str = "pending"


class ViewerResponse(BaseModel):
    model_file_id: str
    project_id: str
    filename: str
    source_format: str
    status: str
    glb_url: str | None = None
    usdz_url: str | None = None
    qr_url: str | None = None
    last_error: str | None = None
