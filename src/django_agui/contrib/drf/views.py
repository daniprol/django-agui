"""Django REST Framework views for django-agui."""

from __future__ import annotations

from collections.abc import Callable
import inspect
import logging
from typing import Any

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
    get_request_origin,
    parse_run_input_json,
    resolve_allowed_origins,
)

logger = logging.getLogger(__name__)


class AGUIBaseView(APIView):
    """Base class for DRF AG-UI views."""

    run_agent: Callable[..., Any] = None
    translate_event: Callable[[Any], Any] | None = None
    get_system_message: Callable[[Any], str | None] | None = None
    auth_required: bool = False
    allowed_origins: list[str] | None = None
    emit_run_lifecycle_events: bool | None = None
    error_detail_policy: str | None = None
    state_save_policy: str | None = None

    def get_agent(self, request: Request) -> Callable[..., Any]:
        """Get the agent function."""
        if inspect.ismethod(self.run_agent):
            return self.run_agent.__func__
        return self.run_agent

    def get_translator(self, request: Request) -> Callable[[Any], Any] | None:
        """Get the event translator."""
        if self.translate_event is None:
            return None
        if inspect.ismethod(self.translate_event):
            return self.translate_event.__func__
        return self.translate_event

    def _apply_cors_headers(self, response: Any, request: Request) -> None:
        origin = get_request_origin(request)
        allowed_origins = resolve_allowed_origins(self.allowed_origins)
        for key, value in get_cors_headers(origin, allowed_origins).items():
            response[key] = value

    def _error_response(
        self,
        request: Request,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> Response:
        response = Response({"error": message}, status=status_code)
        self._apply_cors_headers(response, request)
        return response

    def _validate_origin_and_auth(self, request: Request) -> Response | None:
        try:
            enforce_origin_and_auth(
                request,
                auth_required=self.auth_required,
                allowed_origins=self.allowed_origins,
            )
        except AGUIRequestError as exc:
            return self._error_response(
                request,
                exc.message,
                status_code=exc.status_code,
            )
        return None

    def options(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Handle CORS preflight requests."""
        response = Response(status=status.HTTP_204_NO_CONTENT)
        self._apply_cors_headers(response, request)
        return response


class AGUIView(AGUIBaseView):
    """DRF AG-UI view with SSE streaming."""

    async def post(self, request: Request) -> Response:
        """Handle POST request with AG-UI RunAgentInput."""
        agent = self.get_agent(request)
        if agent is None:
            return Response(
                {"error": "Agent not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        origin_or_auth_error = self._validate_origin_and_auth(request)
        if origin_or_auth_error is not None:
            return origin_or_auth_error

        try:
            ensure_json_content_type(request.content_type)
            enforce_max_content_length(request)
            input_data = parse_run_input_json(request.body)
        except AGUIRequestError as exc:
            return self._error_response(
                request,
                exc.message,
                status_code=exc.status_code,
            )

        runner = AGUIRunner(
            run_agent=agent,
            request=request,
            translate_event=self.get_translator(request),
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
        self._apply_cors_headers(response, request)
        return response


class AGUIRestView(AGUIBaseView):
    """DRF AG-UI view returning REST response (non-streaming)."""

    async def post(self, request: Request) -> Response:
        """Handle POST request with AG-UI RunAgentInput."""
        agent = self.get_agent(request)
        if agent is None:
            return Response(
                {"error": "Agent not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        origin_or_auth_error = self._validate_origin_and_auth(request)
        if origin_or_auth_error is not None:
            return origin_or_auth_error

        try:
            ensure_json_content_type(request.content_type)
            enforce_max_content_length(request)
            input_data = parse_run_input_json(request.body)
        except AGUIRequestError as exc:
            return self._error_response(
                request,
                exc.message,
                status_code=exc.status_code,
            )

        try:
            runner = AGUIRunner(
                run_agent=agent,
                request=request,
                translate_event=self.get_translator(request),
                get_system_message=self.get_system_message,
                emit_run_lifecycle_events=self.emit_run_lifecycle_events,
                error_detail_policy=self.error_detail_policy,
                state_save_policy=self.state_save_policy,
            )
            collected = await runner.collect(input_data)

            response = Response(
                {
                    "thread_id": collected.thread_id,
                    "run_id": collected.run_id,
                    "events": [e.model_dump(mode="json") for e in collected.events],
                },
                status=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                    if collected.has_error
                    else status.HTTP_200_OK
                ),
            )
            self._apply_cors_headers(response, request)
            return response

        except Exception as exc:
            logger.exception("Error during agent execution")
            return self._error_response(
                request,
                str(exc),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
