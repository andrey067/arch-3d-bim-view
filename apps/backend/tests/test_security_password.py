"""Password hashing round-trip."""
from __future__ import annotations

from app.core.security.password import hash_password, verify_password


def test_hash_and_verify() -> None:
    plain = "correct-horse-battery-staple"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False
