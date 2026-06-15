"""Business logic for Projects — simplified for str IDs."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.features.projects import persistence
from app.features.projects.models import Project


def create_project(
    session: Session,
    *,
    owner_id: str,
    name: str,
    description: str | None = None,
) -> Project:
    if not name or not name.strip():
        raise ValidationError("Project name cannot be empty.")
    return persistence.create_project(session, owner_id=owner_id, name=name, description=description)


def get_project(
    session: Session,
    *,
    project_id: str,
    owner_id: str,
) -> Project:
    project = persistence.get_project_by_id(session, project_id)
    if not project:
        raise NotFoundError("Project not found.")
    if project.owner_id != owner_id:
        raise ForbiddenError("You do not have access to this project.")
    return project


def list_projects(
    session: Session,
    *,
    owner_id: str,
    include_archived: bool = False,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[list[dict], str | None]:
    projects = persistence.list_projects(
        session, owner_id=owner_id, include_archived=include_archived, cursor=cursor, limit=limit
    )
    has_more = len(projects) > limit
    if has_more:
        projects = projects[:limit]
    next_cursor = projects[-1].id if has_more and projects else None

    items = []
    for p in projects:
        file_count = persistence.count_project_files(session, p.id)
        items.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "archived_at": p.archived_at,
            "file_count": file_count,
        })
    return items, next_cursor


def update_project(
    session: Session,
    *,
    project_id: str,
    owner_id: str,
    name: str | None = None,
    description: str | None = None,
) -> Project:
    project = get_project(session, project_id=project_id, owner_id=owner_id)
    if project.archived_at:
        raise ConflictError("Cannot update an archived project.")
    if name is not None and (not name or not name.strip()):
        raise ValidationError("Project name cannot be empty.")
    return persistence.update_project(session, project, name=name, description=description)


def archive_project(
    session: Session,
    *,
    project_id: str,
    owner_id: str,
) -> Project:
    project = get_project(session, project_id=project_id, owner_id=owner_id)
    if project.archived_at:
        return project
    return persistence.archive_project(session, project)


def unarchive_project(
    session: Session,
    *,
    project_id: str,
    owner_id: str,
) -> Project:
    project = get_project(session, project_id=project_id, owner_id=owner_id)
    if not project.archived_at:
        return project
    return persistence.unarchive_project(session, project)


def delete_project(
    session: Session,
    *,
    project_id: str,
    owner_id: str,
) -> None:
    project = get_project(session, project_id=project_id, owner_id=owner_id)
    from app.core.storage.local_disk import LocalDiskStorage
    from app.core.config import get_settings
    from app.features.models import persistence as models_persistence

    settings = get_settings()
    storage = LocalDiskStorage(settings.STORAGE_ROOT)

    model_files = models_persistence.list_model_files(session, project_id=project_id)
    for mf in model_files:
        try:
            storage.delete(mf.original_storage_key)
        except Exception:
            pass

    persistence.delete_project(session, project)
