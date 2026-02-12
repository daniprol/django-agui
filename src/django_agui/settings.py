"""Django AG-UI settings with defaults."""

from __future__ import annotations

from typing import Any, Type

from django.conf import settings
from django.utils.module_loading import import_string


DEFAULTS: dict[str, Any] = {
    "AUTH_BACKEND": "django_agui.backends.auth.django.DjangoAuthBackend",
    "EVENT_ENCODER": "django_agui.encoders.SSEEventEncoder",
    "STATE_BACKEND": None,
    "REQUIRE_AUTHENTICATION": False,
    "ALLOWED_ORIGINS": None,
    "SSE_KEEPALIVE_INTERVAL": 30,
    "SSE_TIMEOUT": 300,
    "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
    "DEBUG": False,
}


def get_agui_settings() -> dict[str, Any]:
    """Get AG-UI settings from Django settings."""
    return getattr(settings, "AGUI", {})


def get_setting(key: str, default: Any = None) -> Any:
    """Get an AG-UI setting with default fallback."""
    agui_settings = get_agui_settings()
    return agui_settings.get(key, DEFAULTS.get(key, default))


def get_backend_class(setting_key: str) -> Type | None:
    """Import and return a backend class from settings or None."""
    path = get_setting(setting_key)
    if path is None:
        return None
    return import_string(path)
