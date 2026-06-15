"""FastAPI application entrypoint.

Simplified MVP: SQLite, BackgroundTasks, no Celery/Redis, no auth.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    from app.core.db import create_tables
    create_tables()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Arch3DAR API",
        version="1.0.0",
        description="Arch3DAR — 3D model viewer with AR support.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.core.logging import CorrelationIdMiddleware
    app.add_middleware(CorrelationIdMiddleware)

    # Register domain error handlers
    from app.core.errors import register_error_handlers
    register_error_handlers(app)

    @app.get("/api/v1/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # --- Projects router ---
    from app.features.projects.router import router as projects_router
    app.include_router(projects_router)

    # --- Models (upload) router ---
    from app.features.models.router import router as models_router
    app.include_router(models_router)

    # --- Conversion (jobs) router ---
    from app.features.conversion.router import router as conversion_router
    app.include_router(conversion_router)

    # --- Sharing router ---
    from app.features.sharing.router import router as sharing_router
    app.include_router(sharing_router)

    # --- Public viewer router ---
    from app.features.viewer.router import router as public_viewer_router
    app.include_router(public_viewer_router)

    return app


app = create_app()
