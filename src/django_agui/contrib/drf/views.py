"""Django REST Framework views for django-agui."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django_agui.runtime import (
    AGUIRequestError,
    AGUIRunner,
    enforce_max_content_length,
    enforce_origin_and_auth,
    ensure_json_content_type,
    get_cors_headers,
    get_error_message,
    get_request_origin,
    parse_run_input_json,
    resolve_allowed_origins,
    resolve_error_policy,
)

logger = logging.getLogger(__name__)


class AGUIBaseView(APIView):
    """Base class for DRF AG-UI views."""

    run_agent: Callable[..., Any] | None = None
    translate_event: Callable[[Any], Any] | None = None
    get_system_message: Callable[[Any], str | None] | None = None
    auth_required: bool = False
    allowed_origins: list[str] | None = None
    emit_run_lifecycle_events: bool | None = None
    error_detail_policy: str | None = None
    state_save_policy: str | None = None

    def get_run_agent(self, request: Request) -> Callable[..., Any] | None:
        """Return the configured agent callable."""
        return self.run_agent

    def get_translate_event(
        self,
        request: Request,
    ) -> Callable[[Any], Any] | None:
        """Return the optional event translator."""
        return self.translate_event

    def get_auth_required(self, request: Request) -> bool:
        """Return whether auth is required for this request."""
        return self.auth_required

    def get_allowed_origins(self, request: Request) -> list[str] | None:
        """Resolve allowed CORS origins for this request."""
        return resolve_allowed_origins(self.allowed_origins)

    def parse_input(self, request: Request):
        """Parse and validate AG-UI input data."""
        ensure_json_content_type(request.content_type)
        enforce_max_content_length(request)
        return parse_run_input_json(request.body)

    def get_runner(
        self,
        request: Request,
        *,
        run_agent: Callable[..., Any],
    ) -> AGUIRunner:
        """Build the AG-UI runner."""
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
        response: Any,
        *,
        origin: str | None,
        allowed_origins: list[str] | None,
    ) -> None:
        """Apply CORS headers to a DRF/Django response."""
        for key, value in get_cors_headers(origin, allowed_origins).items():
            response[key] = value

    def error_response(
        self,
        message: str,
        *,
        status_code: int,
        origin: str | None,
        allowed_origins: list[str] | None,
    ) -> Response:
        """Build an error response with CORS headers."""
        response = Response({"error": message}, status=status_code)
        self.apply_cors_headers(
            response,
            origin=origin,
            allowed_origins=allowed_origins,
        )
        return response

    async def _handle_post(
        self,
        request: Request,
        *,
        streaming: bool,
    ) -> Response | StreamingHttpResponse:
        origin = get_request_origin(request)

        try:
            allowed_origins = self.get_allowed_origins(request)
        except ImproperlyConfigured:
            logger.exception("Invalid AG-UI CORS configuration")
            return self.error_response(
                "Internal server error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                origin=origin,
                allowed_origins=None,
            )

        run_agent = self.get_run_agent(request)
        if run_agent is None:
            return self.error_response(
                "Agent not configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        except AGUIRequestError as exc:
            return self.error_response(
                exc.message,
                status_code=exc.status_code,
                origin=origin,
                allowed_origins=allowed_origins,
            )

        runner = self.get_runner(request, run_agent=run_agent)

        if streaming:
            response = StreamingHttpResponse(
                runner.stream(input_data),
                content_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
            self.apply_cors_headers(
                response,
                origin=origin,
                allowed_origins=allowed_origins,
            )
            return response

        try:
            collected = await runner.collect(input_data)
            response = Response(
                {
                    "thread_id": collected.thread_id,
                    "run_id": collected.run_id,
                    "events": [
                        event.model_dump(mode="json") for event in collected.events
                    ],
                },
                status=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                    if collected.has_error
                    else status.HTTP_200_OK
                ),
            )
            self.apply_cors_headers(
                response,
                origin=origin,
                allowed_origins=allowed_origins,
            )
            return response
        except Exception as exc:
            logger.exception("Unhandled error while processing DRF AG-UI request")
            error_policy = resolve_error_policy(self.error_detail_policy)
            return self.error_response(
                get_error_message(exc, policy=error_policy),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                origin=origin,
                allowed_origins=allowed_origins,
            )

    def options(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Handle CORS preflight requests."""
        origin = get_request_origin(request)
        try:
            allowed_origins = self.get_allowed_origins(request)
        except ImproperlyConfigured:
            logger.exception("Invalid AG-UI CORS configuration")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        self.apply_cors_headers(
            response,
            origin=origin,
            allowed_origins=allowed_origins,
        )
        return response


class AGUIView(AGUIBaseView):
    """DRF AG-UI view with SSE streaming."""

    async def post(self, request: Request, *args: Any, **kwargs: Any):
        """Handle streaming POST requests."""
        return await self._handle_post(request, streaming=True)


class AGUIRestView(AGUIBaseView):
    """DRF AG-UI view returning JSON events (non-streaming)."""

    async def post(self, request: Request, *args: Any, **kwargs: Any):
        """Handle non-streaming POST requests."""
        return await self._handle_post(request, streaming=False)
