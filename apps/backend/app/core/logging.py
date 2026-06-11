"""Structured JSON logging with `correlation_id` propagation.

Logs are emitted to stdout (captured by Docker). Each request gets
a correlation id (read from the `X-Correlation-Id` header or
generated) which is then attached to every log record produced
during that request via a `ContextVar`.
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Correlation-Id"

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": _correlation_id.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Promote known extras
        for key in ("route", "method", "status", "duration_ms", "user_id", "error"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    # Reset handlers so re-configuration (tests) is idempotent
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    # Tame noisy libraries
    logging.getLogger("uvicorn.access").setLevel("WARNING")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Attach a correlation id to every request and emit a structured access log."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        incoming = request.headers.get(CORRELATION_ID_HEADER)
        cid = incoming or str(uuid.uuid4())
        token = _correlation_id.set(cid)
        start = time.perf_counter()
        response: Response
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logging.getLogger("app.request").exception(
                "request failed",
                extra={
                    "route": request.url.path,
                    "method": request.method,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            _correlation_id.reset(token)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers[CORRELATION_ID_HEADER] = cid
        logging.getLogger("app.request").info(
            "request",
            extra={
                "route": request.url.path,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
