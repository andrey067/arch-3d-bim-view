"""Sprint 0 health + observability smoke tests."""
from __future__ import annotations


def test_health_returns_ok(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_correlation_id_is_echoed(client) -> None:
    response = client.get("/api/v1/health", headers={"X-Correlation-Id": "abc-123"})
    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "abc-123"


def test_correlation_id_is_generated_when_missing(client) -> None:
    response = client.get("/api/v1/health")
    cid = response.headers.get("x-correlation-id")
    assert cid is not None and len(cid) > 0


def test_domain_error_envelope(client) -> None:
    from app.core.errors import NotFoundError

    @client.app.get("/__raise_not_found")
    def _raise() -> None:
        raise NotFoundError("missing thing")

    response = client.get("/__raise_not_found")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "missing thing"
    assert "correlation_id" in body["error"]
