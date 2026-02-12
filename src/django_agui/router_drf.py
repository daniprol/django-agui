"""DRF router for django-agui."""

from __future__ import annotations

from typing import Any, Callable

from rest_framework.routers import Route, SimpleRouter

from django_agui.types import AgentMetadata, AgentRunFunc, EventTranslateFunc
from django_agui.views_drf import create_agui_drf_view, create_agui_rest_drf_view


class AGUIRouter(SimpleRouter):
    """Router for AG-UI agents with DRF.

    Usage:
        router = AGUIRouter()
        router.register("agent", my_agent_function, "my-agent")
        urlpatterns = router.urls
    """

    routes = [
        Route(
            url=r"^{prefix}/$",
            mapping={"post": "post"},
            name="{basename}",
            detail=True,
        ),
    ]

    def __init__(self, *args, **kwargs):
        self._agents: dict[str, AgentMetadata] = {}
        super().__init__(*args, **kwargs)

    def register(
        self,
        prefix: str,
        run_agent: AgentRunFunc,
        basename: str | None = None,
        translate_event: EventTranslateFunc | None = None,
        get_system_message: Callable[[Any], str | None] | None = None,
        streaming: bool = True,
    ) -> None:
        """Register an agent with the router.

        Args:
            prefix: URL prefix for the agent
            run_agent: Async function that runs the agent
            basename: Base name for URL (optional)
            translate_event: Optional event translator
            get_system_message: Optional system message function
            streaming: If True, use streaming response (SSE). If False, use REST response.
        """
        key = prefix.strip("/")

        if streaming:
            view_class = create_agui_drf_view(
                run_agent=run_agent,
                translate_event=translate_event,
                get_system_message=get_system_message,
            )
        else:
            view_class = create_agui_rest_drf_view(
                run_agent=run_agent,
                translate_event=translate_event,
                get_system_message=get_system_message,
            )

        self._agents[key] = {
            "view_class": view_class,
            "basename": basename or key,
        }

        self.registry.append((prefix, view_class, basename or key))

    def get_urls(self):
        """Get URL patterns."""
        urls = []

        for prefix, view_class, basename in self.registry:
            url_pattern = f"{prefix}/"
            urls.append(self._wrap_view(view_class, url_pattern, basename))

        return urls

    def _wrap_view(self, view_class, url_pattern, basename):
        """Create URL pattern from view class."""
        from django.urls import path

        return path(url_pattern, view_class.as_view(), name=basename)
