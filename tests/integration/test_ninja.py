"""Integration tests for Django Ninja backend."""

import pytest

# Skip all tests if Django Ninja is not installed
ninja = pytest.importorskip("ninja")

from ag_ui.core import EventType, TextMessageContentEvent

from django_agui.contrib.ninja import (
    NinjaBackend,
    get_ninja_urlpatterns,
    create_ninja_api,
)


class TestNinjaBackend:
    """Test Django Ninja backend functionality."""

    @pytest.mark.asyncio
    async def test_backend_create_api(self):
        """Test creating Ninja API."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        backend = NinjaBackend()
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

        backend = NinjaBackend()
        patterns = backend.get_urlpatterns(
            path_prefix="agent/",
            run_agent=dummy_agent,
        )

        assert len(patterns) == 1


class TestNinjaShortcuts:
    """Test Ninja shortcut functions."""

    @pytest.mark.asyncio
    async def test_get_ninja_urlpatterns(self):
        """Test get_ninja_urlpatterns shortcut."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        patterns = get_ninja_urlpatterns("agent/", dummy_agent)

        assert len(patterns) == 1

    @pytest.mark.asyncio
    async def test_create_ninja_api(self):
        """Test create_ninja_api shortcut."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        api = create_ninja_api(dummy_agent)

        assert api is not None
