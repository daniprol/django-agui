"""URL configuration helpers for django-agui."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.urls import path

from django_agui.types import AgentRunFunc, EventTranslateFunc, GetSystemMessageFunc
from django_agui.views import AGUIView


@dataclass(slots=True)
class AgentRoute:
    """Configuration for one AG-UI endpoint."""

    path_prefix: str
    run_agent: AgentRunFunc
    translate_event: EventTranslateFunc | None = None
    get_system_message: GetSystemMessageFunc | None = None
    auth_required: bool = False
    allowed_origins: list[str] | None = None
    emit_run_lifecycle_events: bool | None = None
    error_detail_policy: str | None = None
    state_save_policy: str | None = None


def normalize_path_prefix(path_prefix: str) -> str:
    """Normalize URL prefix to Django path format."""
    normalized = path_prefix.strip("/")
    return f"{normalized}/" if normalized else ""


def build_route_name(prefix: str, path_prefix: str) -> str:
    """Build a deterministic Django URL name for an endpoint."""
    normalized = path_prefix.strip("/").replace("/", "-")
    suffix = normalized or "root"
    return f"{prefix}-{suffix}"


def get_agui_urlpatterns(
    path_prefix: str,
    run_agent: AgentRunFunc,
    translate_event: EventTranslateFunc | None = None,
    get_system_message: GetSystemMessageFunc | None = None,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
    emit_run_lifecycle_events: bool | None = None,
    error_detail_policy: str | None = None,
    state_save_policy: str | None = None,
) -> list:
    """Get URL patterns for a single AG-UI agent endpoint."""
    normalized_path = normalize_path_prefix(path_prefix)
    return [
        path(
            normalized_path,
            AGUIView.as_view(
                run_agent=run_agent,
                translate_event=translate_event,
                get_system_message=get_system_message,
                auth_required=auth_required,
                allowed_origins=allowed_origins,
                emit_run_lifecycle_events=emit_run_lifecycle_events,
                error_detail_policy=error_detail_policy,
                state_save_policy=state_save_policy,
            ),
            name=build_route_name("agui", path_prefix),
        )
    ]


class AGUIRouter:
    """Simple multi-agent router for Django URL patterns."""

    view_class = AGUIView
    route_name_prefix = "agui"

    def __init__(self) -> None:
        self._routes: list[AgentRoute] = []

    def register(
        self,
        path_prefix: str,
        run_agent: AgentRunFunc,
        translate_event: EventTranslateFunc | None = None,
        get_system_message: GetSystemMessageFunc | None = None,
        auth_required: bool = False,
        allowed_origins: list[str] | None = None,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
    ) -> None:
        """Register an AG-UI endpoint."""
        self._routes.append(
            AgentRoute(
                path_prefix=path_prefix,
                run_agent=run_agent,
                translate_event=translate_event,
                get_system_message=get_system_message,
                auth_required=auth_required,
                allowed_origins=allowed_origins,
                emit_run_lifecycle_events=emit_run_lifecycle_events,
                error_detail_policy=error_detail_policy,
                state_save_policy=state_save_policy,
            )
        )

    def get_view_kwargs(self, route: AgentRoute) -> dict[str, Any]:
        """Build ``as_view`` kwargs for one route.

        Override in subclasses to inject custom attributes.
        """
        return {
            "run_agent": route.run_agent,
            "translate_event": route.translate_event,
            "get_system_message": route.get_system_message,
            "auth_required": route.auth_required,
            "allowed_origins": route.allowed_origins,
            "emit_run_lifecycle_events": route.emit_run_lifecycle_events,
            "error_detail_policy": route.error_detail_policy,
            "state_save_policy": route.state_save_policy,
        }

    def get_urlpattern(self, route: AgentRoute):
        """Build one Django URL pattern."""
        return path(
            normalize_path_prefix(route.path_prefix),
            self.view_class.as_view(**self.get_view_kwargs(route)),
            name=build_route_name(self.route_name_prefix, route.path_prefix),
        )

    @property
    def urls(self) -> list:
        """Return all registered URL patterns."""
        return [self.get_urlpattern(route) for route in self._routes]


class MultiAgentRouter(AGUIRouter):
    """Alias kept for readability in user code."""

    pass
