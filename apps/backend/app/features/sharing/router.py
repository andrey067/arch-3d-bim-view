"""FastAPI routes for VS-Sharing (ShareLink).

Endpoints (authenticated):
    POST   /api/v1/files/{id}/share   — create share link
    GET    /api/v1/shares              — list share links
    DELETE /api/v1/shares/{id}         — revoke share link
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.features.auth.service import get_current_user
from app.features.sharing import service
from app.features.sharing.schemas import (
    CreateShareRequest,
    ShareCreateResponse,
    ShareListItem,
    ShareListResponse,
)

router = APIRouter(tags=["sharing"])


def _get_user(authorization: str, db: Session):
    """Extract and validate the current user from the Authorization header."""
    from app.core.errors import UnauthorizedError

    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header.")
    token = authorization.removeprefix("Bearer ").strip()
    return get_current_user(db, token=token)


@router.post(
    "/api/v1/files/{file_id}/share",
    response_model=ShareCreateResponse,
    status_code=201,
)
def create_share(
    file_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ShareCreateResponse:
    """Create a public share link for a converted model file.

    Returns the share ID, raw token, and public URL.
    The token is only returned at creation time.
    """
    user = _get_user(authorization, db)
    share, public_url = service.create_share_link(
        db, user_id=user.id, model_file_id=file_id
    )
    db.commit()
    return ShareCreateResponse(
        share_id=share.id,
        token=share.token,
        public_url=public_url,
    )


@router.get(
    "/api/v1/shares",
    response_model=ShareListResponse,
)
def list_shares(
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> ShareListResponse:
    """List all share links for the authenticated user's projects.

    Tokens are NOT exposed in the response.
    """
    user = _get_user(authorization, db)
    shares = service.list_share_links(db, user_id=user.id)
    return ShareListResponse(
        items=[ShareListItem.model_validate(s) for s in shares]
    )


@router.delete("/api/v1/shares/{share_id}", status_code=204)
def revoke_share(
    share_id: uuid.UUID,
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> None:
    """Revoke a share link. Idempotent — 204 even if already revoked."""
    user = _get_user(authorization, db)
    service.revoke_share_link(db, user_id=user.id, share_id=share_id)
    db.commit()
