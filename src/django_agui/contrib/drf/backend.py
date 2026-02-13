"""Django REST Framework backend for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django_agui.contrib.drf.views import AGUIRestView, AGUIView


class DRFBackend:
    """Django REST Framework backend for AG-UI.

    Usage:
        backend = DRFBackend()
        view = backend.create_view(run_agent=my_agent)
        urlpatterns = backend.get_urlpatterns("agent/", my_agent)
    """

    def create_view(
        self,
        run_agent: Callable[..., Any],
        translate_event: Callable[[Any], Any] | None = None,
        get_system_message: Callable[[Any], str | None] | None = None,
        auth_required: bool = False,
        allowed_origins: list[str] | None = None,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
        streaming: bool = True,
        **kwargs: Any,
    ) -> type:
        """Create a DRF view class.

        Args:
            run_agent: Async function that runs the agent
            translate_event: Optional event translator
            get_system_message: Optional system message function
            auth_required: Whether authentication is required
            allowed_origins: CORS origins for this endpoint
            emit_run_lifecycle_events: Override lifecycle event emission
            error_detail_policy: "safe" or "full" error details in RUN_ERROR
            state_save_policy: "always", "on_snapshot", or "disabled"
            streaming: If True, use SSE streaming. If False, use REST response.
            **kwargs: Additional options passed to the view

        Returns:
            DRF view class
        """
        base_class = AGUIView if streaming else AGUIRestView

        # Create a new view class with the agent configured
        class ConfiguredView(base_class):
            pass

        ConfiguredView.run_agent = run_agent
        ConfiguredView.translate_event = translate_event
        ConfiguredView.get_system_message = get_system_message
        ConfiguredView.auth_required = auth_required
        ConfiguredView.allowed_origins = allowed_origins
        ConfiguredView.emit_run_lifecycle_events = emit_run_lifecycle_events
        ConfiguredView.error_detail_policy = error_detail_policy
        ConfiguredView.state_save_policy = state_save_policy

        # Apply any additional attributes from kwargs
        for key, value in kwargs.items():
            setattr(ConfiguredView, key, value)

        return ConfiguredView

    def get_urlpatterns(
        self,
        path_prefix: str,
        run_agent: Callable[..., Any],
        streaming: bool = True,
        **kwargs: Any,
    ) -> list:
        """Get DRF URL patterns.

        Args:
            path_prefix: URL path prefix (e.g., "agent/")
            run_agent: Async function that runs the agent
            streaming: If True, use SSE streaming
            **kwargs: Additional options

        Returns:
            List of Django URL patterns
        """
        from django.urls import path

        view_class = self.create_view(
            run_agent=run_agent,
            streaming=streaming,
            **kwargs,
        )

        normalized = path_prefix.strip("/")
        agent_path = f"{normalized}/" if normalized else ""

        return [
            path(agent_path, view_class.as_view(), name="drf-agui-agent"),
        ]
