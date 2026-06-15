"""FastAPI routes for ShareLink — open access (no auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.identity import DEFAULT_OWNER_ID
from app.features.sharing import service
from app.features.sharing.schemas import (
    CreateShareRequest,
    ShareCreateResponse,
    ShareListItem,
    ShareListResponse,
)

router = APIRouter(tags=["sharing"])


@router.post(
    "/api/v1/files/{file_id}/share",
    response_model=ShareCreateResponse,
    status_code=201,
)
def create_share(
    file_id: str,
    db: Session = Depends(get_db),
) -> ShareCreateResponse:
    share, public_url = service.create_share_link(
        db, user_id=DEFAULT_OWNER_ID, model_file_id=file_id,
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
    db: Session = Depends(get_db),
) -> ShareListResponse:
    shares = service.list_share_links(db, user_id=DEFAULT_OWNER_ID)
    return ShareListResponse(
        items=[ShareListItem.model_validate(s) for s in shares]
    )


@router.delete("/api/v1/shares/{share_id}", status_code=204)
def revoke_share(
    share_id: str,
    db: Session = Depends(get_db),
) -> None:
    service.revoke_share_link(db, user_id=DEFAULT_OWNER_ID, share_id=share_id)
    db.commit()
