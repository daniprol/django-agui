"""Agents package for django-agui."""

from django_agui.agents.registry import (
    AgentRegistry,
    get_agent_config,
    load_agents_from_settings,
)

__all__ = [
    "AgentRegistry",
    "get_agent_config",
    "load_agents_from_settings",
]
