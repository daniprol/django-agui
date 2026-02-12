"""E2E tests for django-agui.

These tests simulate real HTTP requests to the AG-UI endpoints.
"""

import pytest

from ag_ui.core import EventType, TextMessageContentEvent, TextMessageStartEvent


@pytest.mark.e2e
class TestCoreViews:
    """E2E tests for core Django views."""

    @pytest.mark.asyncio
    async def test_basic_request(self, async_client):
        """Test basic agent request."""

        async def dummy_agent(input_data, request):
            yield TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id="msg-1",
            )
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Hello",
            )

        # Create proper RunAgentInput with all required fields
        from ag_ui.core import RunAgentInput

        input_data = RunAgentInput(
            thread_id="test-thread",
            run_id="test-run",
            messages=[],
            state=None,
            tools=[],
            context=[],
            forwardedProps=None,
        )

        # Mock request
        class MockRequest:
            pass

        events = []
        async for event in dummy_agent(input_data, MockRequest()):
            events.append(event)

        assert len(events) == 2
        assert events[0].type == EventType.TEXT_MESSAGE_START
        assert events[1].type == EventType.TEXT_MESSAGE_CONTENT


@pytest.mark.e2e
class TestEndToEndFlow:
    """Complete end-to-end flow tests."""

    @pytest.mark.asyncio
    async def test_full_agent_execution(self):
        """Test complete agent execution flow."""
        from ag_ui.core import (
            RunAgentInput,
            RunStartedEvent,
            RunFinishedEvent,
        )

        async def complete_agent(input_data, request):
            # Start event
            yield RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )

            # Content event
            yield TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg-1",
                delta="Processing...",
            )

            # Finish event
            yield RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )

        input_data = RunAgentInput(
            thread_id="test-thread",
            run_id="test-run",
            messages=[],
            state=None,
            tools=[],
            context=[],
            forwardedProps=None,
        )

        class MockRequest:
            pass

        events = []
        async for event in complete_agent(input_data, MockRequest()):
            events.append(event)

        assert len(events) == 3
        assert events[0].type == EventType.RUN_STARTED
        assert events[1].type == EventType.TEXT_MESSAGE_CONTENT
        assert events[2].type == EventType.RUN_FINISHED
