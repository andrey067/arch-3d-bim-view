"""SQLAlchemy 2 engine, session factory, and FastAPI dependency.

Worker Celery is synchronous, so we keep the engine sync here.
Alembic uses the same `DATABASE_URL` via `env.py` (T005).
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models (Sprint 1+ entities)."""


def _build_engine() -> object:
    settings = get_settings()
    url = settings.DATABASE_URL
    # SQLite doesn't support pool_size/max_overflow
    if url.startswith("sqlite"):
        return create_engine(url, echo=False)
    return create_engine(
        url,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        future=True,
    )


engine = _build_engine()
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
