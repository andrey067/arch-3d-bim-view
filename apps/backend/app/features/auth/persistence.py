"""Auth-specific database queries."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.features.auth.models import RefreshToken, User


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_user_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    return session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def create_user(
    session: Session,
    *,
    email: str,
    password_hash: str,
    display_name: str | None = None,
) -> User:
    user = User(email=email, password_hash=password_hash, display_name=display_name)
    session.add(user)
    session.flush()
    return user


def save_refresh_token(
    session: Session,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(token)
    session.flush()
    return token


def get_refresh_token_by_hash(
    session: Session, token_hash: str
) -> RefreshToken | None:
    return session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()


def revoke_refresh_token(session: Session, token_id: uuid.UUID) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.id == token_id)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    session.flush()
