"""Django AG-UI settings with defaults.

Similar to django-a2a, provides a centralized settings system
for configuring django-agui backends and options.
"""

from __future__ import annotations

from typing import Any, Type

from django.conf import settings
from django.utils.module_loading import import_string


DEFAULTS: dict[str, Any] = {
    # Core settings
    "AUTH_BACKEND": "django_agui.backends.auth.DjangoAuthBackend",
    "EVENT_ENCODER": "django_agui.encoders.SSEEventEncoder",
    "STATE_BACKEND": None,
    # Security
    "REQUIRE_AUTHENTICATION": False,
    "ALLOWED_ORIGINS": None,
    # SSE settings
    "SSE_KEEPALIVE_INTERVAL": 30,
    "SSE_TIMEOUT": 300,
    # Request limits
    "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
    # Framework backend classes (can be overridden)
    "DRF_BACKEND": "django_agui.contrib.drf.backend.DRFBackend",
    "NINJA_BACKEND": "django_agui.contrib.ninja.backend.NinjaBackend",
    "BOLT_BACKEND": "django_agui.contrib.bolt.backend.BoltBackend",
    # Debug mode
    "DEBUG": False,
}


def get_agui_settings() -> dict[str, Any]:
    """Get AG-UI settings from Django settings.

    Returns:
        Dict containing AG-UI configuration from Django settings.
    """
    return getattr(settings, "AGUI", {})


def get_setting(key: str, default: Any = None) -> Any:
    """Get an AG-UI setting with default fallback.

    Args:
        key: Setting key to retrieve
        default: Default value if setting not found

    Returns:
        Setting value or default
    """
    agui_settings = get_agui_settings()
    return agui_settings.get(key, DEFAULTS.get(key, default))


def get_backend_class(setting_key: str) -> Type | None:
    """Import and return a backend class from settings.

    Args:
        setting_key: Key for the backend class setting

    Returns:
        Backend class or None if not configured
    """
    path = get_setting(setting_key)
    if path is None:
        return None
    return import_string(path)
