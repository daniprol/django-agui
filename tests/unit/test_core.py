"""Unit tests for django-agui core functionality."""

import pytest
from django.conf import settings

from ag_ui.core import (
    EventType,
    TextMessageContentEvent,
    TextMessageStartEvent,
)

from django_agui import VERSION
from django_agui.encoders import SSEEventEncoder
from django_agui.settings import get_setting, get_agui_settings, get_backend_class


class _DummyBackend:
    pass


class TestVersion:
    """Test version information."""

    def test_version_is_string(self):
        """Test that VERSION is a string."""
        assert isinstance(VERSION, str)
        assert VERSION == "0.2.0"


class TestSSEEncoder:
    """Test SSE event encoder."""

    def test_encode_text_message_start(self):
        """Test encoding TEXT_MESSAGE_START event."""
        encoder = SSEEventEncoder()
        event = TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id="msg-1",
        )
        encoded = encoder.encode(event)

        assert encoded.startswith('data: {"')
        assert "TEXT_MESSAGE_START" in encoded
        assert "msg-1" in encoded

    def test_encode_text_message_content(self):
        """Test encoding TEXT_MESSAGE_CONTENT event."""
        encoder = SSEEventEncoder()
        event = TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="Hello world",
        )
        encoded = encoder.encode(event)

        assert encoded.startswith('data: {"')
        assert "TEXT_MESSAGE_CONTENT" in encoded
        assert "Hello world" in encoded

    def test_encode_keepalive(self):
        """Test encoding keepalive message."""
        encoder = SSEEventEncoder()
        encoded = encoder.encode_keepalive()

        assert ": keepalive" in encoded


class TestSettings:
    """Test settings functionality."""

    def test_get_agui_settings_empty(self):
        """Test getting empty AGUI settings."""
        settings.AGUI = {}
        agui_settings = get_agui_settings()
        assert agui_settings == {}

    def test_get_agui_settings_with_values(self):
        """Test getting AGUI settings with values."""
        settings.AGUI = {"TEST_KEY": "test_value"}
        agui_settings = get_agui_settings()
        assert agui_settings.get("TEST_KEY") == "test_value"

    def test_get_setting_with_default(self):
        """Test getting setting with default fallback."""
        settings.AGUI = {}
        value = get_setting("NONEXISTENT", "default")
        assert value == "default"

    def test_get_setting_from_defaults(self):
        """Test getting setting from DEFAULTS."""
        settings.AGUI = {}
        value = get_setting("SSE_TIMEOUT")
        assert value == 300  # From DEFAULTS

    def test_get_setting_override(self):
        """Test overriding default setting."""
        settings.AGUI = {"SSE_TIMEOUT": 600}
        value = get_setting("SSE_TIMEOUT")
        assert value == 600

    def test_get_backend_class_none(self):
        """Test getting None backend class."""
        settings.AGUI = {"TEST_BACKEND": None}
        result = get_backend_class("TEST_BACKEND")
        assert result is None

    def test_get_backend_class_invalid(self):
        """Test getting invalid backend class."""
        settings.AGUI = {"TEST_BACKEND": "invalid.module.Class"}
        with pytest.raises(ImportError):
            get_backend_class("TEST_BACKEND")

    def test_get_backend_class_from_type(self):
        """Test backend class from direct type setting."""
        settings.AGUI = {"TEST_BACKEND": _DummyBackend}
        assert get_backend_class("TEST_BACKEND") is _DummyBackend

    def test_get_backend_class_from_instance(self):
        """Test backend class from direct instance setting."""
        settings.AGUI = {"TEST_BACKEND": _DummyBackend()}
        assert get_backend_class("TEST_BACKEND") is _DummyBackend
