"""Django REST Framework integration for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    from django_agui.contrib.drf.backend import DRFBackend
    from django_agui.contrib.drf.views import AGUIRestView, AGUIView
except ImportError as exc:
    raise ImportError(
        "Django REST Framework is not installed. "
        "Install it with: pip install djangorestframework"
    ) from exc

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
    """Shortcut for ``DRFBackend().get_urlpatterns(...)``."""
    return DRFBackend().get_urlpatterns(
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
    """Shortcut for ``DRFBackend().create_view(...)``."""
    return DRFBackend().create_view(
        run_agent=run_agent,
        streaming=streaming,
        **kwargs,
    )
