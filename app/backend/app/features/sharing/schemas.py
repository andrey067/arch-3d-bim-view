"""Pydantic v2 schemas for ShareLink request/response contracts."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CreateShareRequest(BaseModel):
    model_file_id: str


class ShareCreateResponse(BaseModel):
    share_id: str
    token: str
    public_url: str


class ShareListItem(BaseModel):
    id: str
    model_file_id: str
    project_id: str
    created_at: datetime
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class ShareListResponse(BaseModel):
    items: list[ShareListItem]


class PublicShareManifest(BaseModel):
    model_file_id: str
    filename: str
    source_format: str
    status: str
    glb_url: str
    usdz_url: str | None = None
    qr_url: str | None = None
