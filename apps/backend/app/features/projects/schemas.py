"""Pydantic v2 schemas for VS-Projects request/response contracts."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(None, max_length=2000)


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    file_count: int = 0

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectListItem]
    next_cursor: str | None = None
