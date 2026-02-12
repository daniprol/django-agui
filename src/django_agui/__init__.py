"""Django AG-UI - Django integration for the AG-UI protocol."""

from django_agui.decorators import agui_view
from django_agui.urls import AGUIRouter, MultiAgentRouter, get_agui_urlpatterns

__all__ = [
    "AGUIRouter",
    "MultiAgentRouter",
    "get_agui_urlpatterns",
    "agui_view",
    "VERSION",
]

VERSION = "0.1.0"
