"""FastAPI routes for VS-Projects.

Endpoints:
    POST   /api/v1/projects              — create project
    GET    /api/v1/projects              — list projects
    GET    /api/v1/projects/{id}         — project detail
    PATCH  /api/v1/projects/{id}         — update project
    POST   /api/v1/projects/{id}/archive   — archive project
    POST   /api/v1/projects/{id}/unarchive — unarchive project
    DELETE /api/v1/projects/{id}         — delete project
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.features.auth.service import get_current_user
from app.features.projects import service
from app.features.projects.schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectListItem,
    ProjectResponse,
    UpdateProjectRequest,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _get_user(authorization: str, db: Session):
    """Extract and validate the current user from the Authorization header."""
    from app.core.errors import UnauthorizedError

    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header.")
    token = authorization.removeprefix("Bearer ").strip()
    return get_current_user(db, token=token)


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: CreateProjectRequest,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    user = _get_user(authorization, db)
    project = service.create_project(db, owner_id=user.id, name=body.name, description=body.description)
    db.commit()
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    archived: bool = Query(False, description="Include archived projects"),
    cursor: str | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    user = _get_user(authorization, db)
    items, next_cursor = service.list_projects(
        db, owner_id=user.id, include_archived=archived, cursor=cursor, limit=limit
    )
    return ProjectListResponse(items=[ProjectListItem(**i) for i in items], next_cursor=next_cursor)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    user = _get_user(authorization, db)
    project = service.get_project(db, project_id=project_id, owner_id=user.id)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: uuid.UUID,
    body: UpdateProjectRequest,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    user = _get_user(authorization, db)
    project = service.update_project(
        db, project_id=project_id, owner_id=user.id, name=body.name, description=body.description
    )
    db.commit()
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    user = _get_user(authorization, db)
    project = service.archive_project(db, project_id=project_id, owner_id=user.id)
    db.commit()
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
def unarchive_project(
    project_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    user = _get_user(authorization, db)
    project = service.unarchive_project(db, project_id=project_id, owner_id=user.id)
    db.commit()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> None:
    user = _get_user(authorization, db)
    service.delete_project(db, project_id=project_id, owner_id=user.id)
    db.commit()
