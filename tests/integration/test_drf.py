"""Integration tests for DRF backend."""

import pytest

# Skip all tests if DRF is not installed
drf = pytest.importorskip("rest_framework")

from ag_ui.core import EventType, TextMessageContentEvent

from django_agui.contrib.drf import DRFBackend, get_drf_urlpatterns, create_drf_view


class TestDRFBackend:
    """Test DRF backend functionality."""

    @pytest.mark.asyncio
    async def test_backend_create_view(self):
        """Test creating DRF view."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        backend = DRFBackend()
        view_class = backend.create_view(run_agent=dummy_agent)

        assert view_class is not None
        assert view_class.run_agent == dummy_agent

    @pytest.mark.asyncio
    async def test_backend_create_view_with_options(self):
        """Test creating DRF view with options."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        backend = DRFBackend()
        view_class = backend.create_view(
            run_agent=dummy_agent,
            auth_required=True,
            streaming=False,
        )

        assert view_class.auth_required is True

    @pytest.mark.asyncio
    async def test_backend_get_urlpatterns(self):
        """Test getting URL patterns."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        backend = DRFBackend()
        patterns = backend.get_urlpatterns(
            path_prefix="agent/",
            run_agent=dummy_agent,
        )

        assert len(patterns) == 1
        assert str(patterns[0].pattern) == "agent/"


class TestDRFShortcuts:
    """Test DRF shortcut functions."""

    @pytest.mark.asyncio
    async def test_get_drf_urlpatterns(self):
        """Test get_drf_urlpatterns shortcut."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        patterns = get_drf_urlpatterns("agent/", dummy_agent)

        assert len(patterns) == 1
        assert str(patterns[0].pattern) == "agent/"

    @pytest.mark.asyncio
    async def test_create_drf_view(self):
        """Test create_drf_view shortcut."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        view_class = create_drf_view(dummy_agent)

        assert view_class is not None
        assert view_class.run_agent == dummy_agent
