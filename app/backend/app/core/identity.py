"""Open-access identity — no auth required.

All resources are owned by a single default owner in the LAN homelab setup.
"""
from __future__ import annotations

DEFAULT_OWNER_ID = "public"


def default_owner() -> str:
    """FastAPI dependency returning the fixed default owner ID."""
    return DEFAULT_OWNER_ID
