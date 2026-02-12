"""Decorators for django-agui."""

from __future__ import annotations

from typing import Any, Callable

from ag_ui.core import BaseEvent

from django_agui.views import create_agui_view


def agui_view(
    *,
    translate_event: Callable[[Any], Any] | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
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
        )

        # Return the as_view() callable for use in URL patterns
        return view_class.as_view()

    return decorator
