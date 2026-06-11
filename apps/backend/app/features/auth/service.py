"""Auth business logic (VS-Auth).

Orchestrates registration, login, refresh, logout, and user
hydration. All network and persistence concerns are delegated to
router/persistence; this module owns *rules* only.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, UnauthorizedError, ValidationError
from app.core.security import jwt as jwt_mod
from app.core.security import password as password_mod
from app.core.security import refresh as refresh_mod
from app.features.auth import persistence
from app.features.auth.models import User


def _validate_password_strength(password: str, email: str) -> None:
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if password.lower() == email.lower():
        raise ValidationError("Password must not be equal to email.")


def register(
    session: Session,
    *,
    email: str,
    password: str,
    display_name: str | None = None,
) -> User:
    _validate_password_strength(password, email)
    existing = persistence.get_user_by_email(session, email)
    if existing:
        raise ConflictError("Email already registered.")
    hashed = password_mod.hash_password(password)
    return persistence.create_user(
        session, email=email, password_hash=hashed, display_name=display_name
    )


def login(
    session: Session,
    *,
    email: str,
    password: str,
) -> tuple[str, str]:
    user = persistence.get_user_by_email(session, email)
    if not user or not password_mod.verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid credentials.")

    settings = get_settings()
    access_token = jwt_mod.encode_access(str(user.id))
    raw_refresh = refresh_mod.generate()
    token_hash = refresh_mod.hash_token(raw_refresh)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_D)
    persistence.save_refresh_token(
        session, user_id=user.id, token_hash=token_hash, expires_at=expires_at
    )
    session.commit()
    return access_token, raw_refresh


def refresh(
    session: Session,
    *,
    raw_token: str,
) -> tuple[str, str]:
    token_hash = refresh_mod.hash_token(raw_token)
    stored = persistence.get_refresh_token_by_hash(session, token_hash)
    if not stored:
        raise UnauthorizedError("Invalid refresh token.")
    if stored.revoked_at is not None:
        raise UnauthorizedError("Refresh token has been revoked.")
    if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token has expired.")

    user = persistence.get_user_by_id(session, stored.user_id)
    if not user:
        raise UnauthorizedError("User not found.")

    # Revoke the old token
    persistence.revoke_refresh_token(session, stored.id)

    # Issue new pair
    settings = get_settings()
    new_access = jwt_mod.encode_access(str(user.id))
    new_raw_refresh = refresh_mod.generate()
    new_hash = refresh_mod.hash_token(new_raw_refresh)
    new_expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TTL_D)
    persistence.save_refresh_token(
        session, user_id=user.id, token_hash=new_hash, expires_at=new_expires
    )
    session.commit()
    return new_access, new_raw_refresh


def logout(
    session: Session,
    *,
    raw_token: str,
) -> None:
    token_hash = refresh_mod.hash_token(raw_token)
    stored = persistence.get_refresh_token_by_hash(session, token_hash)
    if stored and stored.revoked_at is None:
        persistence.revoke_refresh_token(session, stored.id)
        session.commit()


def get_current_user(
    session: Session,
    *,
    token: str,
) -> User:
    try:
        payload = jwt_mod.decode_access(token)
    except jwt_mod.InvalidTokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Invalid token payload.")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise UnauthorizedError("Invalid user id in token.") from exc
    user = persistence.get_user_by_id(session, user_id)
    if not user:
        raise UnauthorizedError("User not found.")
    if not user.is_active:
        raise UnauthorizedError("User account is deactivated.")
    return user
