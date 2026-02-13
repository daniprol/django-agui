"""Unit tests for django-agui system checks."""

from __future__ import annotations

from django_agui.checks import check_agui_settings


def test_invalid_error_detail_policy(settings):
    """Invalid ERROR_DETAIL_POLICY is reported."""
    settings.AGUI = {"ERROR_DETAIL_POLICY": "verbose"}

    errors = check_agui_settings(None)
    ids = {error.id for error in errors}
    assert "django_agui.E002" in ids


def test_invalid_allowed_origins_type(settings):
    """Invalid ALLOWED_ORIGINS type is reported."""
    settings.AGUI = {"ALLOWED_ORIGINS": "https://example.com"}

    errors = check_agui_settings(None)
    ids = {error.id for error in errors}
    assert "django_agui.E003" in ids
