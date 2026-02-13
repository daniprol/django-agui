"""Django REST Framework views for django-agui."""

from __future__ import annotations

import inspect
import json
import logging
from typing import Any, Callable

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ag_ui.core import (
    EventType,
    RunAgentInput,
    StateSnapshotEvent,
)

from django_agui.runtime import (
    AGUIRunner,
    authenticate_request,
    get_cors_headers,
    get_request_origin,
    is_json_content_type,
    is_origin_allowed,
    prepare_input,
    resolve_allowed_origins,
)
from django_agui.settings import get_setting

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

    def get_allowed_origins(self) -> list[str] | None:
        """Resolve CORS allowed origins."""
        return resolve_allowed_origins(self.allowed_origins)

    def _apply_cors_headers(self, response: Any, request: Request) -> None:
        origin = get_request_origin(request)
        allowed_origins = self.get_allowed_origins()
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
        origin = get_request_origin(request)
        allowed_origins = self.get_allowed_origins()
        if not is_origin_allowed(origin, allowed_origins):
            return self._error_response(
                request,
                "Origin not allowed",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        auth = authenticate_request(request, auth_required=self.auth_required)
        if not auth.allowed:
            return self._error_response(
                request,
                auth.message or "Unauthorized",
                status_code=auth.status_code or status.HTTP_401_UNAUTHORIZED,
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

        if not is_json_content_type(request.content_type):
            return self._error_response(request, "Content-Type must be application/json")

        max_content_length = get_setting("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
        content_length = request.headers.get("Content-Length")
        if content_length and max_content_length is not None:
            try:
                if int(content_length) > int(max_content_length):
                    return self._error_response(
                        request,
                        "Payload too large",
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    )
            except ValueError:
                pass

        try:
            input_data = RunAgentInput.model_validate_json(request.body)
        except json.JSONDecodeError as exc:
            return self._error_response(request, f"Invalid JSON: {exc}")
        except Exception as exc:
            return self._error_response(request, f"Invalid request: {exc}")

        runner = AGUIRunner(
            run_agent=agent,
            request=request,
            translate_event=self.get_translator(request),
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

        if not is_json_content_type(request.content_type):
            return self._error_response(request, "Content-Type must be application/json")

        max_content_length = get_setting("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
        content_length = request.headers.get("Content-Length")
        if content_length and max_content_length is not None:
            try:
                if int(content_length) > int(max_content_length):
                    return self._error_response(
                        request,
                        "Payload too large",
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    )
            except ValueError:
                pass

        try:
            input_data = RunAgentInput.model_validate_json(request.body)
        except json.JSONDecodeError as exc:
            return self._error_response(request, f"Invalid JSON: {exc}")
        except Exception as exc:
            return self._error_response(request, f"Invalid request: {exc}")

        events = []
        state_to_save = input_data.state

        try:
            prepared_input, state_backend = await prepare_input(
                input_data,
                request,
                self.get_system_message,
            )
            translator = self.get_translator(request)
            async for event in agent(prepared_input, request):
                if translator:
                    async for translated in translator(event):
                        if (
                            translated.type == EventType.STATE_SNAPSHOT
                            and isinstance(translated, StateSnapshotEvent)
                        ):
                            state_to_save = translated.snapshot
                        events.append(translated)
                else:
                    if (
                        event.type == EventType.STATE_SNAPSHOT
                        and isinstance(event, StateSnapshotEvent)
                    ):
                        state_to_save = event.snapshot
                    events.append(event)

            if state_backend is not None and state_to_save is not None:
                save_result = state_backend.save_state(
                    prepared_input.thread_id,
                    prepared_input.run_id,
                    state_to_save,
                )
                if inspect.isawaitable(save_result):
                    await save_result

            response = Response(
                {
                    "thread_id": prepared_input.thread_id,
                    "run_id": prepared_input.run_id,
                    "events": [e.model_dump(mode="json") for e in events],
                }
            )
            self._apply_cors_headers(response, request)
            return response

        except Exception as exc:
            logger.exception("Error during agent execution")
            response = Response(
                {
                    "error": str(exc),
                    "thread_id": input_data.thread_id,
                    "run_id": input_data.run_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            self._apply_cors_headers(response, request)
            return response
