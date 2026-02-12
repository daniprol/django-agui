"""Integration tests for Django Bolt backend."""

import pytest

# Skip all tests if Django Bolt is not installed
bolt = pytest.importorskip("django_bolt")

from ag_ui.core import EventType, TextMessageContentEvent

from django_agui.contrib.bolt import BoltBackend, get_bolt_urlpatterns, create_bolt_api


class TestBoltBackend:
    """Test Django Bolt backend functionality."""

    @pytest.mark.asyncio
    async def test_backend_create_api(self):
        """Test creating Bolt API."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        backend = BoltBackend()
        api = backend.create_api(run_agent=dummy_agent)

        assert api is not None

    @pytest.mark.asyncio
    async def test_backend_get_urlpatterns(self):
        """Test getting URL patterns."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        backend = BoltBackend()
        patterns = backend.get_urlpatterns(
            path_prefix="agent/",
            run_agent=dummy_agent,
        )

        assert len(patterns) == 1


class TestBoltShortcuts:
    """Test Bolt shortcut functions."""

    @pytest.mark.asyncio
    async def test_get_bolt_urlpatterns(self):
        """Test get_bolt_urlpatterns shortcut."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        patterns = get_bolt_urlpatterns("agent/", dummy_agent)

        assert len(patterns) == 1

    @pytest.mark.asyncio
    async def test_create_bolt_api(self):
        """Test create_bolt_api shortcut."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        api = create_bolt_api(dummy_agent)

        assert api is not None
