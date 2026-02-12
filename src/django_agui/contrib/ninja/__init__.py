"""Django Ninja integration for django-agui."""

from __future__ import annotations

from typing import Any, Callable

try:
    # These imports require django-ninja to be installed
    from django_agui.contrib.ninja.backend import NinjaBackend
except ImportError as e:
    raise ImportError(
        "Django Ninja is not installed. Install it with: pip install django-ninja"
    ) from e

__all__ = [
    "NinjaBackend",
    "get_ninja_urlpatterns",
    "create_ninja_api",
]


def get_ninja_urlpatterns(
    path_prefix: str,
    run_agent: Callable[..., Any],
    **kwargs: Any,
) -> list:
    """Get Django Ninja URL patterns for an agent.

    Args:
        path_prefix: URL path prefix (e.g., "agent/")
        run_agent: Async function that runs the agent
        **kwargs: Additional options

    Returns:
        List of Django URL patterns
    """
    backend = NinjaBackend()
    return backend.get_urlpatterns(
        path_prefix=path_prefix,
        run_agent=run_agent,
        **kwargs,
    )


def create_ninja_api(
    run_agent: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    """Create a Django Ninja API instance.

    Args:
        run_agent: Async function that runs the agent
        **kwargs: Additional options

    Returns:
        NinjaAPI instance
    """
    backend = NinjaBackend()
    return backend.create_api(
        run_agent=run_agent,
        **kwargs,
    )
