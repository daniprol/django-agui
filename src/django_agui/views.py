"""Views for django-agui."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    StreamingHttpResponse,
)
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from django_agui.runtime import (
    AGUIRequestError,
    AGUIRunner,
    enforce_max_content_length,
    enforce_origin_and_auth,
    ensure_json_content_type,
    get_cors_headers,
    get_request_origin,
    parse_run_input_json,
    resolve_allowed_origins,
)

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
    state_save_policy: str | None = None

    async def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        """Handle POST request with AG-UI RunAgentInput."""
        origin = get_request_origin(request)
        try:
            allowed_origins = resolve_allowed_origins(self.allowed_origins)
        except Exception:
            logger.exception("Invalid AG-UI CORS configuration")
            return self._error_response(
                "Internal server error",
                status=500,
                origin=origin,
            )

        if self.run_agent is None:
            return self._error_response(
                "Agent not configured",
                status=500,
                origin=origin,
                allowed_origins=allowed_origins,
            )

        try:
            ensure_json_content_type(request.content_type)
            enforce_max_content_length(request)
            origin, allowed_origins = enforce_origin_and_auth(
                request,
                auth_required=self.auth_required,
                allowed_origins=allowed_origins,
            )
            input_data = parse_run_input_json(request.body)

            runner = AGUIRunner(
                run_agent=self.run_agent,
                request=request,
                translate_event=self.translate_event,
                get_system_message=self.get_system_message,
                emit_run_lifecycle_events=self.emit_run_lifecycle_events,
                error_detail_policy=self.error_detail_policy,
                state_save_policy=self.state_save_policy,
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

        except AGUIRequestError as exc:
            return self._error_response(
                exc.message,
                status=exc.status_code,
                origin=origin,
                allowed_origins=allowed_origins,
            )
        except Exception:
            logger.exception("Unhandled error while processing AG-UI request")
            return self._error_response(
                "Internal server error",
                status=500,
                origin=origin,
                allowed_origins=allowed_origins,
            )

    async def get(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBadRequest:
        """Handle GET request - not supported for agent execution."""
        return HttpResponseBadRequest(
            "AG-UI endpoint requires POST requests",
            content_type="text/plain",
        )

    async def options(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        """Handle CORS preflight requests."""
        origin = get_request_origin(request)
        try:
            allowed_origins = resolve_allowed_origins(self.allowed_origins)
        except Exception:
            logger.exception("Invalid AG-UI CORS configuration")
            return HttpResponse(status=500)
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
    state_save_policy: str | None = None,
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
    ConfiguredAGUIView.state_save_policy = state_save_policy

    return ConfiguredAGUIView
