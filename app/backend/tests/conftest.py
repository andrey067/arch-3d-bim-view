"""Pytest fixtures — open access, no auth."""
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Force a deterministic, non-prod config for tests BEFORE importing app.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["STORAGE_ROOT"] = "/tmp/test-storage-arch3dar"

from app.core.db import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def db_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    """Yield a session that rolls back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session, db_engine) -> Iterator[TestClient]:
    """Create a test client that uses the test session."""
    def _override_get_db():
        yield db_session

    from app.core import db as db_module
    original_engine = db_module.engine
    db_module.engine = db_engine

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()

    db_module.engine = original_engine


@pytest.fixture()
def tmp_storage(tmp_path):
    """Provide a temporary storage directory for tests."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    original = os.environ.get("STORAGE_ROOT")
    os.environ["STORAGE_ROOT"] = str(storage_dir)
    yield storage_dir
    if original:
        os.environ["STORAGE_ROOT"] = original
