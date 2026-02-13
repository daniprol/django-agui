"""Core Django AG-UI views."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
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
    """Main Django AG-UI view.

    Customize behavior by subclassing and overriding hook methods such as
    ``get_run_agent`` or ``get_runner``.
    """

    http_method_names = ["post", "options"]

    run_agent: Callable[..., Any] | None = None
    translate_event: Callable[[Any], Any] | None = None
    get_system_message: Callable[[Any], str | None] | None = None
    auth_required: bool = False
    allowed_origins: list[str] | None = None
    emit_run_lifecycle_events: bool | None = None
    error_detail_policy: str | None = None
    state_save_policy: str | None = None

    def get_run_agent(self, request: HttpRequest) -> Callable[..., Any] | None:
        """Return the agent callable for this request."""
        return self.run_agent

    def get_translate_event(
        self,
        request: HttpRequest,
    ) -> Callable[[Any], Any] | None:
        """Return the optional event translator."""
        return self.translate_event

    def get_auth_required(self, request: HttpRequest) -> bool:
        """Return whether authentication is required."""
        return self.auth_required

    def get_allowed_origins(self, request: HttpRequest) -> list[str] | None:
        """Resolve allowed CORS origins for this request."""
        return resolve_allowed_origins(self.allowed_origins)

    def parse_input(self, request: HttpRequest):
        """Parse and validate the AG-UI input payload."""
        ensure_json_content_type(request.content_type)
        enforce_max_content_length(request)
        return parse_run_input_json(request.body)

    def get_runner(
        self,
        request: HttpRequest,
        *,
        run_agent: Callable[..., Any],
    ) -> AGUIRunner:
        """Build the AG-UI runner for this request."""
        return AGUIRunner(
            run_agent=run_agent,
            request=request,
            translate_event=self.get_translate_event(request),
            get_system_message=self.get_system_message,
            emit_run_lifecycle_events=self.emit_run_lifecycle_events,
            error_detail_policy=self.error_detail_policy,
            state_save_policy=self.state_save_policy,
        )

    def apply_cors_headers(
        self,
        response: HttpResponse,
        *,
        origin: str | None,
        allowed_origins: list[str] | None,
    ) -> None:
        """Apply CORS headers to the response."""
        for key, value in get_cors_headers(origin, allowed_origins).items():
            response[key] = value

    def build_streaming_response(
        self,
        runner: AGUIRunner,
        input_data: Any,
    ) -> HttpResponse:
        """Build a streaming SSE response."""
        return StreamingHttpResponse(
            runner.stream(input_data),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    def error_response(
        self,
        message: str,
        *,
        status: int,
        origin: str | None,
        allowed_origins: list[str] | None,
    ) -> HttpResponse:
        """Build an error response with CORS headers."""
        response = HttpResponse(message, status=status, content_type="text/plain")
        self.apply_cors_headers(
            response,
            origin=origin,
            allowed_origins=allowed_origins,
        )
        return response

    async def post(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Handle AG-UI POST requests."""
        origin = get_request_origin(request)

        try:
            allowed_origins = self.get_allowed_origins(request)
        except ImproperlyConfigured:
            logger.exception("Invalid AG-UI CORS configuration")
            return self.error_response(
                "Internal server error",
                status=500,
                origin=origin,
                allowed_origins=None,
            )

        run_agent = self.get_run_agent(request)
        if run_agent is None:
            return self.error_response(
                "Agent not configured",
                status=500,
                origin=origin,
                allowed_origins=allowed_origins,
            )

        try:
            origin, allowed_origins = enforce_origin_and_auth(
                request,
                auth_required=self.get_auth_required(request),
                allowed_origins=allowed_origins,
            )
            input_data = self.parse_input(request)
            response = self.build_streaming_response(
                self.get_runner(request, run_agent=run_agent),
                input_data,
            )
            self.apply_cors_headers(
                response,
                origin=origin,
                allowed_origins=allowed_origins,
            )
            return response
        except AGUIRequestError as exc:
            return self.error_response(
                exc.message,
                status=exc.status_code,
                origin=origin,
                allowed_origins=allowed_origins,
            )
        except Exception:
            logger.exception("Unhandled error while processing AG-UI request")
            return self.error_response(
                "Internal server error",
                status=500,
                origin=origin,
                allowed_origins=allowed_origins,
            )

    async def options(
        self,
        request: HttpRequest,
        *args: Any,
        **kwargs: Any,
    ) -> HttpResponse:
        """Handle CORS preflight requests."""
        origin = get_request_origin(request)
        try:
            allowed_origins = self.get_allowed_origins(request)
        except ImproperlyConfigured:
            logger.exception("Invalid AG-UI CORS configuration")
            return HttpResponse(status=500)

        response = HttpResponse(status=204)
        self.apply_cors_headers(
            response,
            origin=origin,
            allowed_origins=allowed_origins,
        )
        return response
