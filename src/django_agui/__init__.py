"""Django AG-UI - Django integration for the AG-UI protocol."""

from django_agui.decorators import agui_view
from django_agui.urls import AGUIRouter, get_agui_urlpatterns

__all__ = [
    "AGUIRouter",
    "get_agui_urlpatterns",
    "agui_view",
    "VERSION",
]

VERSION = "0.2.0"
