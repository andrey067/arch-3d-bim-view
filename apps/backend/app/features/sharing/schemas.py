"""Pydantic v2 schemas for VS-Sharing (ShareLink) request/response contracts."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateShareRequest(BaseModel):
    """Request body for creating a share link."""
    model_file_id: uuid.UUID


class ShareCreateResponse(BaseModel):
    """Response after creating a share link."""
    share_id: uuid.UUID
    token: str
    public_url: str


class ShareListItem(BaseModel):
    """A single share link in a list (token NOT exposed)."""
    id: uuid.UUID
    model_file_id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class ShareListResponse(BaseModel):
    """Response for listing share links."""
    items: list[ShareListItem]


class PublicShareManifest(BaseModel):
    """Public manifest for a share link — returned to anonymous clients."""
    model_file_id: uuid.UUID
    filename: str
    source_format: str
    status: str
    glb_url: str
    thumbnail_url: str | None = None
