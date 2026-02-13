"""Django Bolt backend for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class BoltBackend:
    """Django Bolt backend for AG-UI.

    Usage:
        backend = BoltBackend()
        api = backend.create_api(run_agent=my_agent)
        urlpatterns = backend.get_urlpatterns("agent/", my_agent)
    """

    def create_api(
        self,
        run_agent: Callable[..., Any],
        translate_event: Callable[[Any], Any] | None = None,
        get_system_message: Callable[[Any], str | None] | None = None,
        auth_required: bool = False,
        allowed_origins: list[str] | None = None,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create a Django Bolt API instance.

        Args:
            run_agent: Async function that runs the agent
            translate_event: Optional event translator
            get_system_message: Optional system message function
            auth_required: Whether authentication is required
            allowed_origins: CORS origins for this endpoint
            emit_run_lifecycle_events: Override lifecycle event emission
            error_detail_policy: "safe" or "full" RUN_ERROR payload policy
            state_save_policy: "always", "on_snapshot", or "disabled"
            **kwargs: Additional options passed to BoltAPI

        Returns:
            BoltAPI instance
        """
        try:
            from django_bolt import BoltAPI
        except ImportError as exc:
            raise ImportError(
                "Django Bolt is not installed. Install it with: pip install django-bolt"
            ) from exc

        from django_agui.contrib.bolt.views import create_bolt_endpoint

        # Create API instance
        api = BoltAPI(**kwargs)

        # Create and register the endpoint
        endpoint = create_bolt_endpoint(
            run_agent=run_agent,
            translate_event=translate_event,
            get_system_message=get_system_message,
            auth_required=auth_required,
            allowed_origins=allowed_origins,
            emit_run_lifecycle_events=emit_run_lifecycle_events,
            error_detail_policy=error_detail_policy,
            state_save_policy=state_save_policy,
        )

        # Register the endpoint
        api.post("/")(endpoint)

        return api

    def get_urlpatterns(
        self,
        path_prefix: str,
        run_agent: Callable[..., Any],
        **kwargs: Any,
    ) -> list:
        """Get Django Bolt URL patterns.

        Args:
            path_prefix: URL path prefix (e.g., "agent/")
            run_agent: Async function that runs the agent
            **kwargs: Additional options

        Returns:
            List of Django URL patterns
        """
        from django.urls import path

        api = self.create_api(run_agent=run_agent, **kwargs)

        normalized = path_prefix.strip("/")

        return [
            path(f"{normalized}/", api.urls),
        ]
