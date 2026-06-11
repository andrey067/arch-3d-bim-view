"""Business logic for VS-Sharing (ShareLink).

Orchestrates share link creation, listing, revocation, and token
resolution. No network concerns — those belong in the router.
"""
from __future__ import annotations

import logging
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.features.models.models import ConversionJob, JobStatus, ModelFile
from app.features.projects import persistence as projects_persistence
from app.features.sharing.models import ShareLink

logger = logging.getLogger(__name__)


def _generate_token() -> str:
    """Generate a cryptographically secure random token (256 bits hex)."""
    return secrets.token_hex(32)


def create_share_link(
    session: Session,
    *,
    user_id: uuid.UUID,
    model_file_id: uuid.UUID,
) -> tuple[ShareLink, str]:
    """Create a public share link for a model file.

    Returns the ShareLink and the raw token. The token is only
    returned at creation time.

    Raises:
        NotFoundError: Model file not found.
        ForbiddenError: User doesn't own the project.
        ConflictError: Conversion not ready.
    """
    model_file = session.get(ModelFile, model_file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    project = projects_persistence.get_project_by_id(session, model_file.project_id)
    if project is None or project.owner_id != user_id:
        raise ForbiddenError("You do not have access to this model file.")

    # Verify conversion is ready
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
        id=uuid.uuid4(),
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
    user_id: uuid.UUID,
) -> list[ShareLink]:
    """List all share links for projects owned by the user."""
    # Get all project IDs owned by the user
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
    user_id: uuid.UUID,
    share_id: uuid.UUID,
) -> None:
    """Revoke a share link. Idempotent — no error if already revoked.

    Raises:
        NotFoundError: Share link not found.
        ForbiddenError: User doesn't own the project.
    """
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
    """Resolve a share token to a ShareLink.

    Returns None if the token is invalid or the link is revoked.
    """
    share = session.scalar(
        select(ShareLink).where(ShareLink.token == token)
    )
    if share is None or share.revoked_at is not None:
        return None
    return share
