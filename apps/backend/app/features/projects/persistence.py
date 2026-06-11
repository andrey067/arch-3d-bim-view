"""Database queries for VS-Projects."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.features.projects.models import Project


def create_project(
    session: Session,
    *,
    owner_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> Project:
    project = Project(owner_id=owner_id, name=name.strip(), description=description)
    session.add(project)
    session.flush()
    return project


def get_project_by_id(session: Session, project_id: uuid.UUID) -> Project | None:
    return session.get(Project, project_id)


def list_projects(
    session: Session,
    *,
    owner_id: uuid.UUID,
    include_archived: bool = False,
    cursor: str | None = None,
    limit: int = 20,
) -> list[Project]:
    stmt = select(Project).where(Project.owner_id == owner_id)
    if not include_archived:
        stmt = stmt.where(Project.archived_at.is_(None))
    if cursor:
        try:
            cursor_dt = uuid.UUID(cursor)
        except ValueError:
            cursor_dt = None
        if cursor_dt:
            stmt = stmt.where(Project.id > cursor_dt)
    stmt = stmt.order_by(Project.created_at.desc()).limit(limit + 1)
    return list(session.scalars(stmt).all())


def count_project_files(session: Session, project_id: uuid.UUID) -> int:
    from app.features.models.models import ModelFile

    stmt = select(func.count()).select_from(ModelFile).where(ModelFile.project_id == project_id)
    return session.scalar(stmt) or 0


def update_project(
    session: Session,
    project: Project,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Project:
    if name is not None:
        project.name = name.strip()
    if description is not None:
        project.description = description
    session.flush()
    return project


def archive_project(session: Session, project: Project) -> Project:
    from datetime import datetime, timezone

    project.archived_at = datetime.now(timezone.utc)
    session.flush()
    return project


def unarchive_project(session: Session, project: Project) -> Project:
    project.archived_at = None
    session.flush()
    return project


def delete_project(session: Session, project: Project) -> None:
    session.delete(project)
    session.flush()
