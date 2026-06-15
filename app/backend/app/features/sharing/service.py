"""Business logic for ShareLink — simplified for str IDs."""
from __future__ import annotations

import logging
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.features.models.models import ConversionJob, JobStatus, ModelFile
from app.features.projects import persistence as projects_persistence
from app.features.sharing.models import ShareLink

logger = logging.getLogger(__name__)


def _generate_token() -> str:
    return secrets.token_hex(32)


def create_share_link(
    session: Session,
    *,
    user_id: str,
    model_file_id: str,
) -> tuple[ShareLink, str]:
    model_file = session.get(ModelFile, model_file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    project = projects_persistence.get_project_by_id(session, model_file.project_id)
    if project is None or project.owner_id != user_id:
        raise ForbiddenError("You do not have access to this model file.")

    job = session.scalar(
        select(ConversionJob)
        .where(ConversionJob.model_file_id == model_file_id)
        .order_by(ConversionJob.created_at.desc())
        .limit(1)
    )
    if job is None or job.status != JobStatus.ready:
        raise ConflictError("Model conversion is not ready yet.")

    token = _generate_token()

    share = ShareLink(
        token=token,
        project_id=model_file.project_id,
        model_file_id=model_file_id,
        created_by=user_id,
    )
    session.add(share)
    session.flush()

    settings = get_settings()
    public_url = f"{settings.PUBLIC_BASE_URL}/s/{token}"

    logger.info("Share link created: %s for model %s", share.id, model_file_id)

    return share, public_url


def list_share_links(
    session: Session,
    *,
    user_id: str,
) -> list[ShareLink]:
    from app.features.projects.models import Project

    project_ids = session.scalars(
        select(Project.id).where(Project.owner_id == user_id)
    ).all()

    if not project_ids:
        return []

    shares = session.scalars(
        select(ShareLink)
        .where(ShareLink.project_id.in_(project_ids))
        .order_by(ShareLink.created_at.desc())
    ).all()

    return list(shares)


def revoke_share_link(
    session: Session,
    *,
    user_id: str,
    share_id: str,
) -> None:
    from datetime import datetime, timezone

    share = session.get(ShareLink, share_id)
    if share is None:
        raise NotFoundError("Share link not found.")

    project = projects_persistence.get_project_by_id(session, share.project_id)
    if project is None or project.owner_id != user_id:
        raise ForbiddenError("You do not have access to this share link.")

    if share.revoked_at is None:
        share.revoked_at = datetime.now(timezone.utc)
        session.flush()
        logger.info("Share link revoked: %s", share_id)


def resolve_token(
    session: Session,
    *,
    token: str,
) -> ShareLink | None:
    share = session.scalar(
        select(ShareLink).where(ShareLink.token == token)
    )
    if share is None or share.revoked_at is not None:
        return None
    return share
