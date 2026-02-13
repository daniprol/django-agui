"""Django Bolt integration for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    # These imports require django-bolt to be installed
    from django_agui.contrib.bolt.backend import BoltBackend
except ImportError as e:
    raise ImportError(
        "Django Bolt is not installed. Install it with: pip install django-bolt"
    ) from e

__all__ = [
    "BoltBackend",
    "get_bolt_urlpatterns",
    "create_bolt_api",
]


def get_bolt_urlpatterns(
    path_prefix: str,
    run_agent: Callable[..., Any],
    **kwargs: Any,
) -> list:
    """Get Django Bolt URL patterns for an agent.

    Args:
        path_prefix: URL path prefix (e.g., "agent/")
        run_agent: Async function that runs the agent
        **kwargs: Additional options

    Returns:
        List of Django URL patterns
    """
    backend = BoltBackend()
    return backend.get_urlpatterns(
        path_prefix=path_prefix,
        run_agent=run_agent,
        **kwargs,
    )


def create_bolt_api(
    run_agent: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    """Create a Django Bolt API instance.

    Args:
        run_agent: Async function that runs the agent
        **kwargs: Additional options

    Returns:
        BoltAPI instance
    """
    backend = BoltBackend()
    return backend.create_api(
        run_agent=run_agent,
        **kwargs,
    )
