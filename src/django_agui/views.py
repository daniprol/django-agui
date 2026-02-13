"""Views for django-agui."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ag_ui.core import RunAgentInput

from django_agui.runtime import (
    AGUIRunner,
    authenticate_request,
    get_cors_headers,
    get_request_origin,
    is_json_content_type,
    is_origin_allowed,
    resolve_allowed_origins,
)
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

    http_method_names = ["post", "get", "options"]

    run_agent: Callable[..., Any] = None
    translate_event: Callable[[Any], Any] | None = None
    get_system_message: Callable[[Any], str | None] | None = None
    auth_required: bool = False
    allowed_origins: list[str] | None = None
    emit_run_lifecycle_events: bool | None = None
    error_detail_policy: str | None = None

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

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
        if "emit_run_lifecycle_events" in kwargs:
            self.emit_run_lifecycle_events = kwargs["emit_run_lifecycle_events"]
        if "error_detail_policy" in kwargs:
            self.error_detail_policy = kwargs["error_detail_policy"]
        return self

    async def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        """Handle POST request with AG-UI RunAgentInput."""
        if self.run_agent is None:
            return self._error_response("Agent not configured")

        try:
            if not is_json_content_type(request.content_type):
                return HttpResponseBadRequest(
                    "Content-Type must be application/json",
                    content_type="text/plain",
                )

            origin = get_request_origin(request)
            allowed_origins = resolve_allowed_origins(self.allowed_origins)
            if not is_origin_allowed(origin, allowed_origins):
                return self._error_response(
                    "Origin not allowed",
                    status=403,
                    origin=origin,
                    allowed_origins=allowed_origins,
                )

            auth = authenticate_request(request, auth_required=self.auth_required)
            if not auth.allowed:
                return self._error_response(
                    auth.message or "Unauthorized",
                    status=auth.status_code or 401,
                    origin=origin,
                    allowed_origins=allowed_origins,
                )

            max_content_length = get_setting("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
            content_length = request.headers.get("Content-Length")
            if content_length and max_content_length is not None:
                try:
                    if int(content_length) > int(max_content_length):
                        return self._error_response(
                            "Payload too large",
                            status=413,
                            origin=origin,
                            allowed_origins=allowed_origins,
                        )
                except ValueError:
                    pass

            try:
                body = request.body
                input_data = RunAgentInput.model_validate_json(body)
            except json.JSONDecodeError as exc:
                return self._error_response(
                    f"Invalid JSON: {exc}",
                    origin=origin,
                    allowed_origins=allowed_origins,
                )
            except Exception as exc:
                return self._error_response(
                    f"Invalid request: {exc}",
                    origin=origin,
                    allowed_origins=allowed_origins,
                )

            runner = AGUIRunner(
                run_agent=self.run_agent,
                request=request,
                translate_event=self.translate_event,
                get_system_message=self.get_system_message,
                emit_run_lifecycle_events=self.emit_run_lifecycle_events,
                error_detail_policy=self.error_detail_policy,
            )

            response = StreamingHttpResponse(
                runner.stream(input_data),
                content_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
            self._apply_cors_headers(response, origin, allowed_origins)
            return response

        except Exception:
            logger.exception("Unhandled error while processing AG-UI request")
            return self._error_response("Internal server error", status=500)

    async def get(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBadRequest:
        """Handle GET request - not supported for agent execution."""
        return HttpResponseBadRequest(
            "AG-UI endpoint requires POST requests",
            content_type="text/plain",
        )

    async def options(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Handle CORS preflight requests."""
        origin = get_request_origin(request)
        allowed_origins = resolve_allowed_origins(self.allowed_origins)
        response = HttpResponse(status=204)
        self._apply_cors_headers(response, origin, allowed_origins)
        return response

    def _apply_cors_headers(
        self,
        response: HttpResponse,
        origin: str | None,
        allowed_origins: list[str] | None,
    ) -> None:
        for key, value in get_cors_headers(origin, allowed_origins).items():
            response[key] = value

    def _error_response(
        self,
        message: str,
        *,
        status: int = 400,
        origin: str | None = None,
        allowed_origins: list[str] | None = None,
    ) -> HttpResponse:
        """Create an error response."""
        response = HttpResponse(message, status=status, content_type="text/plain")
        self._apply_cors_headers(response, origin, allowed_origins)
        return response


def create_agui_view(
    run_agent: Callable[..., Any],
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
    emit_run_lifecycle_events: bool | None = None,
    error_detail_policy: str | None = None,
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
    ConfiguredAGUIView.emit_run_lifecycle_events = emit_run_lifecycle_events
    ConfiguredAGUIView.error_detail_policy = error_detail_policy

    return ConfiguredAGUIView
