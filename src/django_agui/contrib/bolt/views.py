"""Django Bolt views for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.http import StreamingHttpResponse

from django_agui.runtime import (
    AGUIRequestError,
    AGUIRunner,
    enforce_origin_and_auth,
    get_cors_headers,
    parse_run_input_payload,
)


def create_bolt_endpoint(
    run_agent: Callable[..., Any],
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
    emit_run_lifecycle_events: bool | None = None,
    error_detail_policy: str | None = None,
    state_save_policy: str | None = None,
) -> Callable[..., Any]:
    """Create a Django Bolt endpoint function.

    Args:
        run_agent: Async function that runs the agent
        translate_event: Optional event translator
        get_system_message: Optional system message function
        auth_required: Whether authentication is required
        allowed_origins: CORS origins for this endpoint
        emit_run_lifecycle_events: Override lifecycle event emission
        error_detail_policy: "safe" or "full" RUN_ERROR payload policy
        state_save_policy: "always", "on_snapshot", or "disabled"

    Returns:
        Async endpoint function for Django Bolt
    """

    async def agent_endpoint(request, body: dict) -> Any:
        """Bolt endpoint handler."""
        try:
            origin, resolved_origins = enforce_origin_and_auth(
                request,
                auth_required=auth_required,
                allowed_origins=allowed_origins,
            )
            input_data = parse_run_input_payload(body)
        except AGUIRequestError as exc:
            from django_bolt.exceptions import HttpException

            raise HttpException(exc.status_code, exc.message) from exc

        runner = AGUIRunner(
            run_agent=run_agent,
            request=request,
            translate_event=translate_event,
            get_system_message=get_system_message,
            emit_run_lifecycle_events=emit_run_lifecycle_events,
            error_detail_policy=error_detail_policy,
            state_save_policy=state_save_policy,
        )
        response = StreamingHttpResponse(
            runner.stream(input_data),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
        for key, value in get_cors_headers(origin, resolved_origins).items():
            response[key] = value
        return response

    return agent_endpoint
