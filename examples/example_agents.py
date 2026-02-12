"""Example agent implementations for django-agui.

This file demonstrates various ways to use django-agui.
"""

from ag_ui.core import (
    EventType,
    TextMessageContentEvent,
    TextMessageStartEvent,
    TextMessageEndEvent,
    RunAgentInput,
)


async def simple_echo_agent(input_data: RunAgentInput, request):
    """Simple echo agent that responds with the user's message."""
    # Get user message
    user_message = input_data.messages[-1].content[0].text

    # Start message
    yield TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id="msg-1",
    )

    # Stream response
    yield TextMessageContentEvent(
        type=EventType.TEXT_MESSAGE_CONTENT,
        message_id="msg-1",
        delta=f"Echo: {user_message}",
    )

    # End message
    yield TextMessageEndEvent(
        type=EventType.TEXT_MESSAGE_END,
        message_id="msg-1",
    )


async def streaming_agent(input_data: RunAgentInput, request):
    """Agent that streams word by word."""
    user_message = input_data.messages[-1].content[0].text

    yield TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id="msg-1",
    )

    response = f"You said: {user_message}"

    # Stream word by word
    for word in response.split():
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta=f"{word} ",
        )

    yield TextMessageEndEvent(
        type=EventType.TEXT_MESSAGE_END,
        message_id="msg-1",
    )


async def authenticated_agent(input_data: RunAgentInput, request):
    """Agent that accesses the authenticated user."""
    user = request.user
    user_message = input_data.messages[-1].content[0].text

    yield TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id="msg-1",
    )

    if user.is_authenticated:
        greeting = f"Hello {user.username}!"
    else:
        greeting = "Hello guest!"

    yield TextMessageContentEvent(
        type=EventType.TEXT_MESSAGE_CONTENT,
        message_id="msg-1",
        delta=f"{greeting} You said: {user_message}",
    )

    yield TextMessageEndEvent(
        type=EventType.TEXT_MESSAGE_END,
        message_id="msg-1",
    )


# Example URL configuration:
"""
# urls.py
from django.urls import path
from django_agui import get_agui_urlpatterns, AGUIRouter
from .examples import simple_echo_agent, streaming_agent, authenticated_agent

# Option 1: Single agent
urlpatterns = [
    *get_agui_urlpatterns(
        path_prefix="echo/",
        run_agent=simple_echo_agent,
    ),
]

# Option 2: Multiple agents with router
router = AGUIRouter()
router.register("echo", simple_echo_agent)
router.register("chat", streaming_agent)
router.register("auth", authenticated_agent, auth_required=True)

urlpatterns = router.urls
"""
