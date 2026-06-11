"""Domain error hierarchy and FastAPI handlers.

All business errors inherit from `DomainError` and carry a stable
`code` (string), an HTTP status, and a human-readable message.
Handlers emit a consistent JSON envelope:

    {"error": {"code": "...", "message": "...", "correlation_id": "..."}}

Unhandled exceptions are caught by a 500 handler that never leaks
the stacktrace to the client.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_correlation_id

_log = logging.getLogger("app.errors")


class DomainError(Exception):
    """Base class for all business-rule errors."""

    code: str = "domain_error"
    status_code: int = 400

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code
        self.details = details or {}


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404


class ForbiddenError(DomainError):
    code = "forbidden"
    status_code = 403


class UnauthorizedError(DomainError):
    code = "unauthorized"
    status_code = 401


class ValidationError(DomainError):
    code = "validation_error"
    status_code = 422


class ConflictError(DomainError):
    code = "conflict"
    status_code = 409


class UnsupportedMediaTypeError(DomainError):
    code = "unsupported_media_type"
    status_code = 415


class RateLimitedError(DomainError):
    code = "rate_limited"
    status_code = 429


def _envelope(code: str, message: str, status: int, details: dict[str, Any] | None = None) -> JSONResponse:
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": get_correlation_id(),
        }
    }
    if details:
        payload["error"]["details"] = details  # type: ignore[index]
    return JSONResponse(payload, status_code=status)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(_: Request, exc: DomainError) -> JSONResponse:
        _log.info(
            "domain error",
            extra={"error": exc.code, "status": exc.status_code},
        )
        return _envelope(exc.code, exc.message, exc.status_code, exc.details)

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        _log.exception("unhandled exception", extra={"error": type(exc).__name__})
        return _envelope(
            "internal_error",
            "An unexpected error occurred.",
            500,
        )
