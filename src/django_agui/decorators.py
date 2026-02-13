"""Decorators for django-agui."""

from __future__ import annotations

from typing import Any, Callable

from django_agui.views import create_agui_view


def agui_view(
    *,
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
    emit_run_lifecycle_events: bool | None = None,
    error_detail_policy: str | None = None,
    state_save_policy: str | None = None,
) -> Callable[..., Any]:
    """Decorator to create an AG-UI view from an async agent function.

    Usage:
        @agui_view()
        async def my_agent(input_data, request):
            yield TextMessageContentEvent(...)

        # In urls.py:
        path('agent/', my_agent)

    Or with options:
        @agui_view(auth_required=True)
        async def my_agent(input_data, request):
            yield TextMessageContentEvent(...)
    """

    def decorator(func: Callable[..., Any]) -> Any:
        # Create a view class configured with the agent
        view_class = create_agui_view(
            run_agent=func,
            translate_event=translate_event,
            get_system_message=get_system_message,
            auth_required=auth_required,
            allowed_origins=allowed_origins,
            emit_run_lifecycle_events=emit_run_lifecycle_events,
            error_detail_policy=error_detail_policy,
            state_save_policy=state_save_policy,
        )

        # Return the as_view() callable for use in URL patterns
        return view_class.as_view()

    return decorator
