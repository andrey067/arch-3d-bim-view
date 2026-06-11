"""Alembic environment.

Reads the SQLAlchemy URL from the application `Settings`, so
`alembic upgrade head` and `alembic revision --autogenerate` work
without duplicating configuration.

All feature models are imported here so that `Base.metadata` is
fully populated for Alembic autogeneration.
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.db import Base

# Import all feature models so Alembic can detect them.
from app.features.auth import models as _auth_models  # noqa: F401
from app.features.projects import models as _project_models  # noqa: F401
from app.features.models import models as _model_file_models  # noqa: F401
from app.features.sharing import models as _share_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
