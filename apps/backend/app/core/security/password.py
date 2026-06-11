"""Password hashing.

`bcrypt` is the Sprint 0 default; the underlying library is
swappable via `Settings.PASSWORD_HASH_SCHEME` in later sprints
without changing call sites.
"""
from __future__ import annotations

from passlib.context import CryptContext

from app.core.config import get_settings

_context: CryptContext | None = None


def _get_context() -> CryptContext:
    global _context
    if _context is None:
        scheme = get_settings().PASSWORD_HASH_SCHEME
        _context = CryptContext(schemes=[scheme], deprecated="auto")
    return _context


def hash_password(plain: str) -> str:
    return _get_context().hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _get_context().verify(plain, hashed)
    except ValueError:
        return False
