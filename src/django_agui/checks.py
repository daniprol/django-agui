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

    error_policy = agui_settings.get("ERROR_DETAIL_POLICY")
    if error_policy is not None and error_policy not in {"safe", "full"}:
        errors.append(
            Error(
                "Invalid AG-UI setting: ERROR_DETAIL_POLICY",
                hint='Use "safe" or "full".',
                obj="django_agui.settings",
                id="django_agui.E002",
            )
        )

    allowed_origins = agui_settings.get("ALLOWED_ORIGINS")
    if allowed_origins is not None and not isinstance(allowed_origins, (list, tuple)):
        errors.append(
            Error(
                "Invalid AG-UI setting: ALLOWED_ORIGINS",
                hint="Use a list/tuple of origins or null.",
                obj="django_agui.settings",
                id="django_agui.E003",
            )
        )

    return errors
