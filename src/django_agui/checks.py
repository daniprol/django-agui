"""Django system checks for django-agui."""

from django.core.checks import Error, Tags, Warning, register


@register(Tags.compatibility)
def check_agui_settings(app_configs, **kwargs):
    """Check AG-UI settings configuration and backend import paths."""
    from django_agui.settings import DEFAULTS, get_agui_settings, get_backend_class

    errors = []
    agui_settings = get_agui_settings()

    for key in agui_settings:
        if key not in DEFAULTS:
            errors.append(
                Warning(
                    f"Unknown AG-UI setting: '{key}'",
                    hint="Check the documentation for valid settings.",
                    obj="django_agui.settings",
                    id="django_agui.W001",
                )
            )

    backend_keys = [
        "AUTH_BACKEND",
        "EVENT_ENCODER",
        "STATE_BACKEND",
    ]

    for setting_key in backend_keys:
        try:
            get_backend_class(setting_key)
        except Exception as exc:
            errors.append(
                Error(
                    f"Invalid backend setting: {setting_key}",
                    hint=str(exc),
                    obj="django_agui.settings",
                    id="django_agui.E001",
                )
            )

    return errors
