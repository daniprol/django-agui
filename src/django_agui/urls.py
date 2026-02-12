"""URL configuration for django-agui."""

from __future__ import annotations

from typing import Any, Callable

from django.urls import path

from django_agui.types import AgentMetadata, AgentRunFunc, EventTranslateFunc
from django_agui.views import create_agui_view


def get_agui_urlpatterns(
    path_prefix: str,
    run_agent: AgentRunFunc,
    translate_event: EventTranslateFunc | None = None,
    get_system_message: Callable[[Any], str | None] | None = None,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
) -> list:
    """Get URL patterns for a single AG-UI agent.

    Args:
        path_prefix: URL prefix for the agent (e.g., "/agent/" or "agent/")
        run_agent: Async function that runs the agent and yields events
        translate_event: Optional function to translate custom events to AG-UI events
        get_system_message: Optional function to get system message
        auth_required: Whether authentication is required
        allowed_origins: List of allowed CORS origins

    Returns:
        List of URL patterns
    """
    normalized = path_prefix.strip("/")
    agent_path = f"{normalized}/" if normalized else ""

    view_class = create_agui_view(
        run_agent=run_agent,
        translate_event=translate_event,
        get_system_message=get_system_message,
        auth_required=auth_required,
        allowed_origins=allowed_origins,
    )

    return [
        path(agent_path, view_class.as_view(), name="agui-agent"),
    ]


class AGUIRouter:
    """Router for AG-UI agents - the main API for creating agent endpoints."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentMetadata] = {}

    def register(
        self,
        path_prefix: str,
        run_agent: AgentRunFunc,
        translate_event: EventTranslateFunc | None = None,
        get_system_message: Callable[[Any], str | None] | None = None,
        auth_required: bool = False,
        allowed_origins: list[str] | None = None,
    ) -> None:
        """Register an agent with the router.

        Args:
            path_prefix: URL prefix (e.g., "echo", "research/agent")
            run_agent: Async function that runs the agent
            translate_event: Optional event translator
            get_system_message: Optional system message function
            auth_required: Whether auth is required
            allowed_origins: CORS origins
        """
        key = path_prefix.strip("/")
        self._agents[key] = AgentMetadata(
            path=key,
            run_agent=run_agent,
            translate_event=translate_event,
            get_system_message=get_system_message,
            auth_required=auth_required,
            allowed_origins=allowed_origins,
        )

    @property
    def urls(self) -> list:
        """Get URL patterns for all registered agents."""
        patterns = []

        for agent_path, metadata in self._agents.items():
            patterns.extend(
                get_agui_urlpatterns(
                    path_prefix=agent_path,
                    run_agent=metadata.run_agent,
                    translate_event=metadata.translate_event,
                    get_system_message=metadata.get_system_message,
                    auth_required=metadata.auth_required,
                    allowed_origins=metadata.allowed_origins,
                )
            )

        return patterns


class MultiAgentRouter(AGUIRouter):
    """Router for multiple AG-UI agents - alias for AGUIRouter."""

    pass
