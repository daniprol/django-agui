"""Tests for django-agui decorators and settings."""

import pytest
from django.conf import settings

from ag_ui.core import EventType, TextMessageContentEvent

from django_agui.decorators import agui_view
from django_agui.settings import get_setting, get_agui_settings


def test_get_agui_settings():
    """Test AG-UI settings retrieval."""
    settings.AGUI = {"TEST_KEY": "test_value"}
    agui_settings = get_agui_settings()
    assert agui_settings.get("TEST_KEY") == "test_value"


def test_get_setting_with_default():
    """Test getting settings with defaults."""
    settings.AGUI = {}
    assert get_setting("NONEXISTENT", "default") == "default"


def test_get_setting_existing():
    """Test getting existing settings."""
    settings.AGUI = {"MAX_CONTENT_LENGTH": 5 * 1024 * 1024}
    assert get_setting("MAX_CONTENT_LENGTH") == 5 * 1024 * 1024


@pytest.mark.asyncio
async def test_agui_view_decorator():
    """Test the @agui_view decorator."""

    @agui_view()
    async def dummy_agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="Hello",
        )

    # The decorator should return a callable (the view's as_view())
    assert callable(dummy_agent)


@pytest.mark.asyncio
async def test_agui_view_decorator_with_options():
    """Test the @agui_view decorator with options."""

    @agui_view(auth_required=True, allowed_origins=["https://example.com"])
    async def protected_agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="Protected",
        )

    # The decorator should return a callable
    assert callable(protected_agent)
