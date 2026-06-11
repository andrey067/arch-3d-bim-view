"""Pydantic v2 schemas for VS-Upload (ModelFile) request/response contracts."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.features.models.models import SourceFormat


class ModelFileResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    uploader_id: uuid.UUID
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
    model_file_id: uuid.UUID
    conversion_job_id: uuid.UUID
    status: str = "pending"


class ViewerResponse(BaseModel):
    """Response model for the viewer endpoint.

    Contains all metadata needed to render a 3D model in the browser.
    """
    model_file_id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    source_format: str
    status: str
    glb_url: str | None = None
    thumbnail_url: str | None = None
    last_error: str | None = None
