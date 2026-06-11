"""Celery worker application for the conversion pipeline.

This module creates the Celery app instance. The worker is started with:
    celery -A app.features.conversion.worker worker --loglevel=info

The backend API and the worker share the same Python codebase but have
separate entrypoints (uvicorn vs celery).
"""
from __future__ import annotations

import os

from celery import Celery

from app.core.config import get_settings


def create_celery_app() -> Celery:
    """Create and configure the Celery application."""
    settings = get_settings()
    broker = str(settings.CELERY_BROKER_URL)
    backend = str(settings.CELERY_RESULT_BACKEND)

    app = Celery(
        "arch3dar",
        broker=broker,
        backend=backend,
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=settings.MAX_CONVERSION_TIMEOUT_S,
        task_soft_time_limit=settings.MAX_CONVERSION_TIMEOUT_S - 30,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=50,
        task_routes={
            "conversion.process_model_file": {"queue": "conversion"},
        },
        task_default_queue="default",
    )

    # Enable eager mode in test environment
    if os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("true", "1"):
        app.conf.task_always_eager = True
        app.conf.task_eager_propagates = os.environ.get(
            "CELERY_TASK_EAGER_PROPAGATES", ""
        ).lower() in ("true", "1")

    # Auto-discover tasks in the conversion package
    app.autodiscover_tasks(["app.features.conversion"])

    return app


# Module-level singleton — Celery CLI needs this for discovery.
celery_app = create_celery_app()
