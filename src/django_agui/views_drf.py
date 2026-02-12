"""Django REST Framework views for django-agui."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.request import Request

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
)

from django_agui.encoders import SSEEventEncoder
from django_agui.settings import get_setting

logger = logging.getLogger(__name__)


class AGUIBaseView(APIView):
    """Base class for AG-UI DRF views."""

    run_agent: Callable[..., Any] = None
    translate_event: Callable[[Any], Any] | None = None
    get_system_message: Callable[[Any], str | None] | None = None

    def get_agent(self, request: Request) -> Callable[..., Any]:
        """Get the agent function. Override for custom logic."""
        return self.run_agent

    def get_translator(self, request: Request) -> Callable[[Any], Any] | None:
        """Get the event translator. Override for custom logic."""
        return self.translate_event

    def get_system_message_func(
        self, request: Request
    ) -> Callable[[Any], str | None] | None:
        """Get the system message function. Override for custom logic."""
        return self.get_system_message


class AGUIView(AGUIBaseView):
    """AG-UI view that returns streaming response."""

    def post(self, request: Request) -> Response:
        """Handle POST request with AG-UI RunAgentInput."""
        agent = self.get_agent(request)
        if agent is None:
            return Response(
                {"error": "Agent not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if request.content_type != "application/json":
            return Response(
                {"error": "Content-Type must be application/json"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            input_data = RunAgentInput.model_validate_json(request.body)
        except json.JSONDecodeError as exc:
            return Response(
                {"error": f"Invalid JSON: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Invalid request: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

                translator = self.get_translator(request)
                async for event in agent(input_data, request):
                    if translator:
                        async for translated in translator(event):
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


class AGUIRestView(AGUIBaseView):
    """AG-UI view that returns a regular REST response (non-streaming)."""

    async def post(self, request: Request) -> Response:
        """Handle POST request with AG-UI RunAgentInput."""
        agent = self.get_agent(request)
        if agent is None:
            return Response(
                {"error": "Agent not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if request.content_type != "application/json":
            return Response(
                {"error": "Content-Type must be application/json"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            input_data = RunAgentInput.model_validate_json(request.body)
        except json.JSONDecodeError as exc:
            return Response(
                {"error": f"Invalid JSON: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Invalid request: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        events = []
        thread_id = input_data.thread_id or "default"
        run_id = input_data.run_id or "default"

        try:
            translator = self.get_translator(request)
            async for event in agent(input_data, request):
                if translator:
                    async for translated in translator(event):
                        events.append(translated)
                else:
                    events.append(event)

            return Response(
                {
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "events": [e.model_dump(mode="json") for e in events],
                }
            )

        except Exception as exc:
            logger.exception("Error during agent execution")
            return Response(
                {
                    "error": str(exc),
                    "thread_id": thread_id,
                    "run_id": run_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def create_agui_drf_view(
    run_agent: Callable[..., Any],
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
) -> type[AGUIView]:
    """Create a DRF AG-UI view class.

    Usage:
        view_class = create_agui_drf_view(my_agent_function)
        urlpatterns = [path('agent/', view_class.as_view())]
    """

    class ConfiguredAGUIView(AGUIView):
        pass

    ConfiguredAGUIView.run_agent = run_agent
    ConfiguredAGUIView.translate_event = translate_event
    ConfiguredAGUIView.get_system_message = get_system_message

    return ConfiguredAGUIView


def create_agui_rest_drf_view(
    run_agent: Callable[..., Any],
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
) -> type[AGUIRestView]:
    """Create a DRF AG-UI REST view class (non-streaming)."""

    class ConfiguredAGUIRestView(AGUIRestView):
        pass

    ConfiguredAGUIRestView.run_agent = run_agent
    ConfiguredAGUIRestView.translate_event = translate_event
    ConfiguredAGUIRestView.get_system_message = get_system_message

    return ConfiguredAGUIRestView
