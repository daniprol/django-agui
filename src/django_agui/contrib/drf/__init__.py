"""Django REST Framework integration for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    # These imports require djangorestframework to be installed
    from django_agui.contrib.drf.backend import DRFBackend
    from django_agui.contrib.drf.views import AGUIRestView, AGUIView
except ImportError as e:
    raise ImportError(
        "Django REST Framework is not installed. "
        "Install it with: pip install djangorestframework"
    ) from e

__all__ = [
    "DRFBackend",
    "AGUIView",
    "AGUIRestView",
    "get_drf_urlpatterns",
    "create_drf_view",
]


def get_drf_urlpatterns(
    path_prefix: str,
    run_agent: Callable[..., Any],
    streaming: bool = True,
    **kwargs: Any,
) -> list:
    """Get DRF URL patterns for an agent.

    Shortcut function to quickly get URL patterns for DRF.

    Args:
        path_prefix: URL path prefix (e.g., "agent/")
        run_agent: Async function that runs the agent
        streaming: If True, use SSE streaming. If False, REST response.
        **kwargs: Additional options

    Returns:
        List of Django URL patterns
    """
    backend = DRFBackend()
    return backend.get_urlpatterns(
        path_prefix=path_prefix,
        run_agent=run_agent,
        streaming=streaming,
        **kwargs,
    )


def create_drf_view(
    run_agent: Callable[..., Any],
    streaming: bool = True,
    **kwargs: Any,
) -> type:
    """Create a DRF view class.

    Shortcut function to create a DRF view.

    Args:
        run_agent: Async function that runs the agent
        streaming: If True, use SSE streaming. If False, REST response.
        **kwargs: Additional options

    Returns:
        DRF view class
    """
    backend = DRFBackend()
    return backend.create_view(
        run_agent=run_agent,
        streaming=streaming,
        **kwargs,
    )
