"""Tests for django-agui."""

import pytest

from ag_ui.core import (
    EventType,
    RunAgentInput,
    TextMessageContentEvent,
    TextMessageStartEvent,
)

from django_agui import AGUIRouter, get_agui_urlpatterns, VERSION
from django_agui.encoders import SSEEventEncoder


def test_version():
    """Test that VERSION is set."""
    assert VERSION == "0.1.0"


def test_sse_encoder():
    """Test SSE event encoder."""
    encoder = SSEEventEncoder()
    event = TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id="msg-1",
    )
    encoded = encoder.encode(event)
    assert "data:" in encoded
    assert "TEXT_MESSAGE_START" in encoded


def test_sse_encoder_keepalive():
    """Test SSE keepalive encoding."""
    encoder = SSEEventEncoder()
    encoded = encoder.encode_keepalive()
    assert ": keepalive" in encoded


@pytest.mark.asyncio
async def test_router_register():
    """Test router registration."""

    async def dummy_agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="Hello",
        )

    router = AGUIRouter()
    router.register("echo", dummy_agent)

    assert "echo" in router._agents
    assert router._agents["echo"].run_agent == dummy_agent


@pytest.mark.asyncio
async def test_get_urlpatterns():
    """Test URL patterns generation."""

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
