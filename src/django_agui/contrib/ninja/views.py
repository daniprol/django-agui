"""Django Ninja views for django-agui."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
)

from django_agui.encoders import SSEEventEncoder

logger = logging.getLogger(__name__)


def create_ninja_endpoint(
    run_agent: Callable[..., Any],
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
    auth_required: bool = False,
) -> Callable[..., Any]:
    """Create a Django Ninja endpoint function.

    Args:
        run_agent: Async function that runs the agent
        translate_event: Optional event translator
        get_system_message: Optional system message function
        auth_required: Whether authentication is required

    Returns:
        Async endpoint function for Django Ninja
    """

    async def agent_endpoint(request, body: dict) -> Any:
        """Ninja endpoint handler."""
        try:
            input_data = RunAgentInput.model_validate(body)
        except Exception as exc:
            from ninja.errors import HttpError

            raise HttpError(400, f"Invalid request: {exc}")

        encoder = SSEEventEncoder()

        async def event_stream():
            thread_id = input_data.thread_id or "default"
            run_id = input_data.run_id or "default"

            try:
                yield encoder.encode(
                    RunStartedEvent(
                        type=EventType.RUN_STARTED,
                        thread_id=thread_id,
                        run_id=run_id,
                    )
                )

                async for event in run_agent(input_data, request):
                    if translate_event:
                        async for translated in translate_event(event):
                            yield encoder.encode(translated)
                    else:
                        yield encoder.encode(event)

                yield encoder.encode(
                    RunFinishedEvent(
                        type=EventType.RUN_FINISHED,
                        thread_id=thread_id,
                        run_id=run_id,
                    )
                )

            except Exception as exc:
                logger.exception("Error during agent execution")
                yield encoder.encode(
                    RunErrorEvent(
                        type=EventType.RUN_ERROR,
                        thread_id=thread_id,
                        run_id=run_id,
                        error_message=str(exc),
                    )
                )

        from django.http import StreamingHttpResponse

        return StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return agent_endpoint
