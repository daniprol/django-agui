"""Django Ninja views for django-agui."""

from __future__ import annotations

from typing import Any, Callable

from ag_ui.core import RunAgentInput
from django.http import StreamingHttpResponse

from django_agui.runtime import (
    AGUIRunner,
    authenticate_request,
    get_cors_headers,
    get_request_origin,
    is_origin_allowed,
    resolve_allowed_origins,
)


def create_ninja_endpoint(
    run_agent: Callable[..., Any],
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
    emit_run_lifecycle_events: bool | None = None,
    error_detail_policy: str | None = None,
) -> Callable[..., Any]:
    """Create a Django Ninja endpoint function.

    Args:
        run_agent: Async function that runs the agent
        translate_event: Optional event translator
        get_system_message: Optional system message function
        auth_required: Whether authentication is required
        allowed_origins: CORS origins for this endpoint
        emit_run_lifecycle_events: Override lifecycle event emission
        error_detail_policy: "safe" or "full" RUN_ERROR payload policy

    Returns:
        Async endpoint function for Django Ninja
    """

    async def agent_endpoint(request, body: dict) -> Any:
        """Ninja endpoint handler."""
        origin = get_request_origin(request)
        resolved_origins = resolve_allowed_origins(allowed_origins)
        if not is_origin_allowed(origin, resolved_origins):
            from ninja.errors import HttpError

            raise HttpError(403, "Origin not allowed")

        auth = authenticate_request(request, auth_required=auth_required)
        if not auth.allowed:
            from ninja.errors import HttpError

            raise HttpError(auth.status_code or 401, auth.message or "Unauthorized")

        try:
            input_data = RunAgentInput.model_validate(body)
        except Exception as exc:
            from ninja.errors import HttpError

            raise HttpError(400, f"Invalid request: {exc}")

        runner = AGUIRunner(
            run_agent=run_agent,
            request=request,
            translate_event=translate_event,
            get_system_message=get_system_message,
            emit_run_lifecycle_events=emit_run_lifecycle_events,
            error_detail_policy=error_detail_policy,
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
