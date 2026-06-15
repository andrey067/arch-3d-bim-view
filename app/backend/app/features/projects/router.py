"""FastAPI routes for Projects — open access (no auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.identity import DEFAULT_OWNER_ID
from app.features.projects import service
from app.features.projects.schemas import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectListItem,
    ProjectResponse,
    UpdateProjectRequest,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: CreateProjectRequest,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = service.create_project(
        db, owner_id=DEFAULT_OWNER_ID, name=body.name, description=body.description,
    )
    db.commit()
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    archived: bool = Query(False, description="Include archived projects"),
    cursor: str | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    items, next_cursor = service.list_projects(
        db, owner_id=DEFAULT_OWNER_ID, include_archived=archived, cursor=cursor, limit=limit,
    )
    return ProjectListResponse(items=[ProjectListItem(**i) for i in items], next_cursor=next_cursor)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = service.get_project(db, project_id=project_id, owner_id=DEFAULT_OWNER_ID)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = service.update_project(
        db, project_id=project_id, owner_id=DEFAULT_OWNER_ID,
        name=body.name, description=body.description,
    )
    db.commit()
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = service.archive_project(db, project_id=project_id, owner_id=DEFAULT_OWNER_ID)
    db.commit()
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
def unarchive_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = service.unarchive_project(db, project_id=project_id, owner_id=DEFAULT_OWNER_ID)
    db.commit()
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> None:
    service.delete_project(db, project_id=project_id, owner_id=DEFAULT_OWNER_ID)
    db.commit()
