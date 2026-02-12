"""Views for django-agui."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from django.http import HttpRequest, HttpResponseBadRequest
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
)
from ag_ui.encoder import EventEncoder

from django_agui.encoders import SSEEventEncoder
from django_agui.settings import get_setting

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class AGUIView(View):
    """Main AG-UI endpoint view that handles agent requests and streams events.

    Usage:
        view = AGUIView.as_view(
            run_agent=my_agent_function,
            translate_event=my_translator,
            auth_required=False,
        )
    """

    http_method_names = ["post", "get"]

    run_agent: Callable[..., Any] = None
    translate_event: Callable[[Any], Any] | None = None
    get_system_message: Callable[[Any], str | None] | None = None
    auth_required: bool = False
    allowed_origins: list[str] | None = None

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._encoder = SSEEventEncoder()

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> "AGUIView":
        """Store view-level attributes from kwargs."""
        super().setup(request, *args, **kwargs)
        if "run_agent" in kwargs:
            self.run_agent = kwargs["run_agent"]
        if "translate_event" in kwargs:
            self.translate_event = kwargs["translate_event"]
        if "get_system_message" in kwargs:
            self.get_system_message = kwargs["get_system_message"]
        if "auth_required" in kwargs:
            self.auth_required = kwargs["auth_required"]
        if "allowed_origins" in kwargs:
            self.allowed_origins = kwargs["allowed_origins"]
        return self

    async def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        """Handle POST request with AG-UI RunAgentInput."""
        if self.run_agent is None:
            return self._error_response("Agent not configured")

        try:
            if request.content_type != "application/json":
                return HttpResponseBadRequest(
                    "Content-Type must be application/json",
                    content_type="text/plain",
                )

            max_content_length = get_setting("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
            content_length = request.headers.get("Content-Length")
            if content_length and max_content_length is not None:
                try:
                    if int(content_length) > int(max_content_length):
                        return HttpResponseBadRequest(
                            "Payload too large",
                            content_type="text/plain",
                        )
                except ValueError:
                    pass

            try:
                body = request.body
                input_data = RunAgentInput.model_validate_json(body)
            except json.JSONDecodeError as exc:
                return self._error_response(f"Invalid JSON: {exc}")
            except Exception as exc:
                return self._error_response(f"Invalid request: {exc}")

            return StreamingResponse(
                self._stream_events(input_data, request),
                content_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

        except Exception:
            logger.exception("Unhandled error while processing AG-UI request")
            return self._error_response("Internal server error")

    async def get(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBadRequest:
        """Handle GET request - not supported for agent execution."""
        return HttpResponseBadRequest(
            "AG-UI endpoint requires POST requests",
            content_type="text/plain",
        )

    async def _stream_events(
        self, input_data: RunAgentInput, request: HttpRequest
    ) -> Any:
        """Stream AG-UI events from the agent."""
        thread_id = input_data.thread_id or "default"
        run_id = input_data.run_id or "default"

        try:
            yield self._encoder.encode(
                RunStartedEvent(
                    type=EventType.RUN_STARTED,
                    thread_id=thread_id,
                    run_id=run_id,
                )
            )

            async for event in self.run_agent(input_data, request):
                if self.translate_event:
                    async for translated in self.translate_event(event):
                        yield self._encoder.encode(translated)
                else:
                    yield self._encoder.encode(event)

            yield self._encoder.encode(
                RunFinishedEvent(
                    type=EventType.RUN_FINISHED,
                    thread_id=thread_id,
                    run_id=run_id,
                )
            )

        except Exception as exc:
            logger.exception("Error during agent execution")
            yield self._encoder.encode(
                RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    thread_id=thread_id,
                    run_id=run_id,
                    error_message=str(exc),
                )
            )

    def _error_response(self, message: str) -> HttpResponseBadRequest:
        """Create an error response."""
        return HttpResponseBadRequest(message, content_type="text/plain")


def create_agui_view(
    run_agent: Callable[..., Any],
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
) -> type[AGUIView]:
    """Create a custom AGUIView class with the specified agent.

    This is a factory function that creates a view class with the agent
    pre-configured, avoiding issues with Django's as_view() method.

    Usage:
        view_class = create_agui_view(my_agent_function)
        urlpatterns = [path('agent/', view_class.as_view())]
    """

    class ConfiguredAGUIView(AGUIView):
        pass

    ConfiguredAGUIView.run_agent = run_agent
    ConfiguredAGUIView.translate_event = translate_event
    ConfiguredAGUIView.get_system_message = get_system_message
    ConfiguredAGUIView.auth_required = auth_required
    ConfiguredAGUIView.allowed_origins = allowed_origins

    return ConfiguredAGUIView
