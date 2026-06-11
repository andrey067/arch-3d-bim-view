"""Redis client singleton + FastAPI dependency.

Used by Celery as broker/result backend (see `conversion/worker.py`
in Sprint 3) and by future rate-limiting / idempotency keys.
"""
from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(
        str(settings.REDIS_URL),
        decode_responses=True,
    )


def get_redis() -> redis.Redis:
    """FastAPI dependency returning the shared Redis client."""
    return get_redis_client()
