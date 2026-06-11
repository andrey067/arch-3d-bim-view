"""Access-token JWT encoding/decoding (Sprint 1 — VS-Auth).

Uses python-jose with HS256 for the MVP. The secret and TTL come
from `Settings` via `get_settings()`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, expired, or tampered."""


def encode_access(user_id: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=settings.ACCESS_TOKEN_TTL_S),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_access(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    sub = payload.get("sub")
    if not sub:
        raise InvalidTokenError("Token missing 'sub' claim.")
    return payload
