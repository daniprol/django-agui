"""Unit tests for django-agui URL routing."""

from ag_ui.core import EventType, TextMessageContentEvent
import pytest

from django_agui.urls import AGUIRouter, get_agui_urlpatterns


class TestAGUIRouter:
    """Test AGUIRouter functionality."""

    @pytest.mark.asyncio
    async def test_router_register_single_agent(self):
        """Test registering a single agent."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        router = AGUIRouter()
        router.register("echo", dummy_agent)

        assert len(router._routes) == 1
        assert router._routes[0].path_prefix == "echo"
        assert router._routes[0].run_agent == dummy_agent

    @pytest.mark.asyncio
    async def test_router_register_multiple_agents(self):
        """Test registering multiple agents."""

        async def agent1(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Agent 1",
            )

        async def agent2(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Agent 2",
            )

        router = AGUIRouter()
        router.register("agent1", agent1)
        router.register("agent2", agent2)

        assert len(router._routes) == 2
        assert router._routes[0].path_prefix == "agent1"
        assert router._routes[1].path_prefix == "agent2"

    @pytest.mark.asyncio
    async def test_router_urls_property(self):
        """Test getting URLs from router."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        router = AGUIRouter()
        router.register("echo", dummy_agent)

        urls = router.urls
        assert len(urls) == 1
        assert str(urls[0].pattern) == "echo/"
        assert urls[0].name == "agui-echo"

    @pytest.mark.asyncio
    async def test_router_register_with_options(self):
        """Test registering with options."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        router = AGUIRouter()
        router.register(
            "protected",
            dummy_agent,
            auth_required=True,
            allowed_origins=["https://example.com"],
        )

        route = router._routes[0]
        assert route.auth_required is True
        assert route.allowed_origins == ["https://example.com"]


class TestGetAguiUrlPatterns:
    """Test get_agui_urlpatterns function."""

    @pytest.mark.asyncio
    async def test_single_url_pattern(self):
        """Test generating single URL pattern."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        patterns = get_agui_urlpatterns(
            path_prefix="agent",
            run_agent=dummy_agent,
        )

        assert len(patterns) == 1
        assert str(patterns[0].pattern) == "agent/"
        assert patterns[0].name == "agui-agent"

    @pytest.mark.asyncio
    async def test_url_pattern_with_slash_prefix(self):
        """Test URL pattern with leading slash."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        patterns = get_agui_urlpatterns(
            path_prefix="/agent/",
            run_agent=dummy_agent,
        )

        assert str(patterns[0].pattern) == "agent/"

    @pytest.mark.asyncio
    async def test_url_pattern_with_options(self):
        """Test URL pattern with options."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        patterns = get_agui_urlpatterns(
            path_prefix="agent",
            run_agent=dummy_agent,
            auth_required=True,
        )

        assert len(patterns) == 1

    @pytest.mark.asyncio
    async def test_route_names_are_unique_by_path(self):
        """Route names should include path suffix to avoid collisions."""

        async def dummy_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        router = AGUIRouter()
        router.register("alpha", dummy_agent)
        router.register("beta", dummy_agent)

        names = [pattern.name for pattern in router.urls]
        assert names == ["agui-alpha", "agui-beta"]
