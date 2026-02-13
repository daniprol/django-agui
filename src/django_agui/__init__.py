"""Django AG-UI - Django integration for the AG-UI protocol."""

from django_agui.agents import AgentRegistry, load_agents_from_settings
from django_agui.decorators import agui_view
from django_agui.integrations import (
    AgentAdapterConfig,
    BaseAgentAdapter,
    FrameworkType,
    LLMConfig,
    LLMProviderType,
)
from django_agui.urls import AGUIRouter, get_agui_urlpatterns

__all__ = [
    "AGUIRouter",
    "get_agui_urlpatterns",
    "agui_view",
    "VERSION",
    "AgentRegistry",
    "load_agents_from_settings",
    "BaseAgentAdapter",
    "AgentAdapterConfig",
    "FrameworkType",
    "LLMConfig",
    "LLMProviderType",
]
