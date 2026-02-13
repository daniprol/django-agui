"""API views for agent execution in django-agui."""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ag_ui.encoder import EventEncoder

from django_agui.agents.registry import AgentRegistry
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


class AgentRunnerView(APIView):
    """DRF view for running registered agents with AG-UI protocol."""

    agent_name: str | None = None
    auth_required: bool = False
    allowed_origins: list[str] | None = None
    emit_run_lifecycle_events: bool | None = None
    error_detail_policy: str | None = None
    state_save_policy: str | None = None

    def get_agent_name(self, request: Request) -> str:
        """Get the agent name from URL or configured value."""
        if self.agent_name:
            return self.agent_name
        return kwargs.get("agent_name")

    def get_allowed_origins(self, request: Request) -> list[str] | None:
        """Resolve allowed CORS origins for this request."""
        return resolve_allowed_origins(self.allowed_origins)

    def parse_input(self, request: Request):
        """Parse and validate AG-UI input data."""
        ensure_json_content_type(request.content_type)
        enforce_max_content_length(request)
        return parse_run_input_json(request.body)

    async def get_agent_runner(
        self,
        request: Request,
        agent_name: str,
    ) -> AGUIRunner | None:
        """Build the AG-UI runner for the specified agent."""
        adapter = await AgentRegistry.get_adapter(agent_name)
        if adapter is None:
            return None

        async def run_agent(input_data, request):
            return adapter.run(input_data)

        return AGUIRunner(
            run_agent=run_agent,
            request=request,
            translate_event=None,
            get_system_message=None,
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
        agent_name: str,
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

        try:
            origin, allowed_origins = enforce_origin_and_auth(
                request,
                auth_required=self.auth_required,
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

        runner = await self.get_agent_runner(request, agent_name)
        if runner is None:
            return self.error_response(
                f"Agent '{agent_name}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
                origin=origin,
                allowed_origins=allowed_origins,
            )

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
            logger.exception("Unhandled error while processing agent request")
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


class AgentStreamView(AgentRunnerView):
    """DRF view for streaming agent responses."""

    async def post(self, request: Request, agent_name: str, *args: Any, **kwargs: Any):
        """Handle streaming POST requests."""
        return await self._handle_post(request, agent_name, streaming=True)


class AgentRestView(AgentRunnerView):
    """DRF view for non-streaming agent responses."""

    async def post(self, request: Request, agent_name: str, *args: Any, **kwargs: Any):
        """Handle non-streaming POST requests."""
        return await self._handle_post(request, agent_name, streaming=False)


class AgentListView(APIView):
    """DRF view for listing registered agents."""

    def get(self, request: Request) -> Response:
        """List all registered agents."""
        agents = AgentRegistry.list_agents()
        return Response({"agents": agents})
