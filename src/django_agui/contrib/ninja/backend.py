"""Django Ninja backend for django-agui."""

from __future__ import annotations

from typing import Any, Callable


class NinjaBackend:
    """Django Ninja backend for AG-UI.

    Usage:
        backend = NinjaBackend()
        api = backend.create_api(run_agent=my_agent)
        urlpatterns = backend.get_urlpatterns("agent/", my_agent)
    """

    def create_api(
        self,
        run_agent: Callable[..., Any],
        translate_event: Callable[[Any], Any] | None = None,
        get_system_message: Callable[[Any], str | None] | None = None,
        auth_required: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Create a Django Ninja API instance.

        Args:
            run_agent: Async function that runs the agent
            translate_event: Optional event translator
            get_system_message: Optional system message function
            auth_required: Whether authentication is required
            **kwargs: Additional options passed to NinjaAPI

        Returns:
            NinjaAPI instance
        """
        try:
            from ninja import NinjaAPI
        except ImportError:
            raise ImportError(
                "Django Ninja is not installed. "
                "Install it with: pip install django-ninja"
            )

        from django_agui.contrib.ninja.views import create_ninja_endpoint

        # Create API instance
        api = NinjaAPI(**kwargs)

        # Create and register the endpoint
        endpoint = create_ninja_endpoint(
            run_agent=run_agent,
            translate_event=translate_event,
            get_system_message=get_system_message,
            auth_required=auth_required,
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
        """Get Django Ninja URL patterns.

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
