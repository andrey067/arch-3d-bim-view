"""FastAPI application entrypoint.

Sprint 1: VS-Auth (register, login, refresh, logout, /me).
Sprint 2: VS-Projects (CRUD) + VS-Upload (file upload/list/delete).
Sprint 3: VS-Conversion (job status, retry, Celery worker).
Sprint 4: VS-Viewer (thumbnail, viewer metadata, GLB serving).
Sprint 5: VS-Sharing (share links) + VS-Public (public viewer).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import CorrelationIdMiddleware, configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="App 3D Viewer API",
        version="0.6.0",
        description="Sprint 5 — Public sharing and anonymous 3D viewer.",
        lifespan=lifespan,
    )

    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/health/ready", tags=["health"])
    async def ready() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    # --- VS-Auth router ---
    from app.features.auth.router import router as auth_router

    app.include_router(auth_router)

    # --- VS-Projects router ---
    from app.features.projects.router import router as projects_router

    app.include_router(projects_router)

    # --- VS-Upload (Models) router ---
    from app.features.models.router import router as models_router

    app.include_router(models_router)

    # --- VS-Conversion (Jobs) router ---
    from app.features.conversion.router import router as conversion_router

    app.include_router(conversion_router)

    # --- VS-Sharing router ---
    from app.features.sharing.router import router as sharing_router

    app.include_router(sharing_router)

    # --- VS-Public (viewer) router ---
    from app.features.viewer.router import router as public_viewer_router

    app.include_router(public_viewer_router)

    register_error_handlers(app)
    return app


app = create_app()
