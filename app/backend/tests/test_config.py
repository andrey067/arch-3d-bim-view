"""Settings unit tests."""
from __future__ import annotations

from app.core.config import get_settings


def test_defaults_present() -> None:
    settings = get_settings()
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.MAX_UPLOAD_MB == 100
    assert settings.IFCCONVERT_PATH == "IfcConvert"
    assert settings.USD_FROM_GLTF_PATH == "usd_from_gltf"


def test_cors_origins_split(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test ,http://c.test")
    settings = get_settings()
    assert settings.CORS_ORIGINS == [
        "http://a.test",
        "http://b.test",
        "http://c.test",
    ]
    get_settings.cache_clear()


def test_is_production(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "prod")
    settings = get_settings()
    assert settings.is_production() is True
    get_settings.cache_clear()
