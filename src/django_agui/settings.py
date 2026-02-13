"""Django settings helpers for django-agui."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils.module_loading import import_string

DEFAULTS: dict[str, Any] = {
    "AUTH_BACKEND": "django_agui.backends.auth.DjangoAuthBackend",
    "EVENT_ENCODER": "django_agui.encoders.SSEEventEncoder",
    "STATE_BACKEND": None,
    "USE_DB_STORAGE": False,
    "REQUIRE_AUTHENTICATION": False,
    "ALLOWED_ORIGINS": None,
    "SSE_KEEPALIVE_INTERVAL": 30,
    "SSE_TIMEOUT": 300,
    "EMIT_RUN_LIFECYCLE_EVENTS": True,
    "ERROR_DETAIL_POLICY": "auto",
    "STATE_SAVE_POLICY": "always",
    "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
    "DEBUG": False,
}


def get_agui_settings() -> dict[str, Any]:
    """Return the AGUI settings dictionary from Django settings."""
    return getattr(settings, "AGUI", {})


def get_setting(key: str, default: Any = None) -> Any:
    """Read one AGUI setting with fallback to defaults."""
    agui_settings = get_agui_settings()
    return agui_settings.get(key, DEFAULTS.get(key, default))


def get_backend_class(setting_key: str) -> type | None:
    """Resolve a backend class from AGUI settings."""
    backend_ref = get_setting(setting_key)
    if backend_ref is None:
        return None
    if isinstance(backend_ref, str):
        return import_string(backend_ref)
    if isinstance(backend_ref, type):
        return backend_ref
    raise TypeError(
        "AGUI."
        f"{setting_key}"
        " must be an import path string or class type, got "
        f"{type(backend_ref).__name__}"
    )
