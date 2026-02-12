"""Unit tests for django-agui decorators."""

import pytest

from ag_ui.core import EventType, TextMessageContentEvent

from django_agui.decorators import agui_view


class TestAguiViewDecorator:
    """Test @agui_view decorator."""

    @pytest.mark.asyncio
    async def test_decorator_basic(self):
        """Test basic decorator usage."""

        @agui_view()
        async def my_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        # Should return a callable (the view)
        assert callable(my_agent)

    @pytest.mark.asyncio
    async def test_decorator_with_auth(self):
        """Test decorator with auth_required."""

        @agui_view(auth_required=True)
        async def protected_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Protected",
            )

        assert callable(protected_agent)

    @pytest.mark.asyncio
    async def test_decorator_with_origins(self):
        """Test decorator with allowed origins."""

        @agui_view(allowed_origins=["https://example.com"])
        async def cors_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="CORS",
            )

        assert callable(cors_agent)

    @pytest.mark.asyncio
    async def test_decorator_with_multiple_options(self):
        """Test decorator with multiple options."""

        @agui_view(
            auth_required=True,
            allowed_origins=["https://example.com", "https://app.com"],
        )
        async def full_agent(input_data, request):
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Full",
            )

        assert callable(full_agent)
