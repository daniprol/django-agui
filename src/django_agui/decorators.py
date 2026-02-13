"""Decorators for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django_agui.views import AGUIView


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
    """Decorate an agent function and return a Django view callable."""

    def decorator(func: Callable[..., Any]) -> Any:
        return AGUIView.as_view(
            run_agent=func,
            translate_event=translate_event,
            get_system_message=get_system_message,
            auth_required=auth_required,
            allowed_origins=allowed_origins,
            emit_run_lifecycle_events=emit_run_lifecycle_events,
            error_detail_policy=error_detail_policy,
            state_save_policy=state_save_policy,
        )

    return decorator
