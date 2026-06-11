"""Refresh-token helpers (Sprint 1 — VS-Auth).

Simplified implementation: single token, SHA-256 hash for storage,
no family revocation (user requested simplicity).
"""
from __future__ import annotations

import hashlib
import secrets


def generate() -> str:
    """Generate a cryptographically secure opaque token (32 bytes hex)."""
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """SHA-256 of an opaque refresh token. Stable across runs."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
