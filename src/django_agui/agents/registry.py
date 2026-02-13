"""Agent registry for django-agui."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from django_agui.integrations.base import (
    AgentAdapterConfig,
    BaseAgentAdapter,
    FrameworkType,
    LLMConfig,
    LLMProviderType,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing agent adapters."""

    _adapters: dict[str, BaseAgentAdapter] = {}
    _adapter_configs: dict[str, AgentAdapterConfig] = {}

    @classmethod
    def register(
        cls,
        name: str,
        config: AgentAdapterConfig,
    ) -> None:
        """Register an agent adapter."""
        cls._adapter_configs[name] = config
        logger.info(f"Registered agent: {name} ({config.framework})")

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister an agent adapter."""
        if name in cls._adapters:
            import asyncio

            asyncio.run(cls._adapters[name].cleanup())
            del cls._adapters[name]
        if name in cls._adapter_configs:
            del cls._adapter_configs[name]
        logger.info(f"Unregistered agent: {name}")

    @classmethod
    async def get_adapter(cls, name: str) -> BaseAgentAdapter | None:
        """Get or create an agent adapter by name."""
        if name in cls._adapters:
            return cls._adapters[name]

        if name not in cls._adapter_configs:
            return None

        config = cls._adapter_configs[name]
        adapter = cls._create_adapter(config)
        await adapter.initialize()
        cls._adapters[name] = adapter
        return adapter

    @classmethod
    def _create_adapter(cls, config: AgentAdapterConfig) -> BaseAgentAdapter:
        """Create an adapter based on framework type."""
        if config.framework == FrameworkType.LANGGRAPH:
            from django_agui.integrations.langgraph import LangGraphAgentAdapter

            return LangGraphAgentAdapter(config)
        elif config.framework == FrameworkType.LLAMAINDEX:
            from django_agui.integrations.llamaindex import LlamaIndexAgentAdapter

            return LlamaIndexAgentAdapter(config)
        elif config.framework == FrameworkType.AGNO:
            from django_agui.integrations.agno import AgnoAgentAdapter

            return AgnoAgentAdapter(config)
        else:
            raise ValueError(f"Unknown framework: {config.framework}")

    @classmethod
    def list_agents(cls) -> list[dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "name": name,
                "framework": config.framework.value,
                "description": config.description,
            }
            for name, config in cls._adapter_configs.items()
        ]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered agents."""
        cls._adapters.clear()
        cls._adapter_configs.clear()


def get_agent_config(name: str) -> AgentAdapterConfig | None:
    """Get agent configuration from Django settings."""
    agents_config = getattr(settings, "AGUI_AGENTS", {})
    agent_config = agents_config.get(name)

    if not agent_config:
        return None

    llm_provider = agent_config.get("llm_provider", "openai")
    model = agent_config.get("model", "gpt-4o")

    llm_config = None
    if llm_provider:
        provider_type = (
            LLMProviderType.OPENAI
            if llm_provider == "openai"
            else LLMProviderType.AZURE_OPENAI
        )

        api_key = None
        if llm_provider == "openai":
            api_key = settings.OPENAI_API_KEY or agent_config.get("api_key")
        elif llm_provider == "azure_openai":
            api_key = settings.AZURE_OPENAI_API_KEY or agent_config.get("api_key")

        base_url = None
        if llm_provider == "azure_openai":
            base_url = settings.AZURE_OPENAI_ENDPOINT or agent_config.get("base_url")

        llm_config = LLMConfig(
            provider=provider_type,
            model=model,
            api_key=api_key,
            base_url=base_url,
            api_version=agent_config.get("api_version"),
            deployment_name=agent_config.get("deployment_name"),
        )

    return AgentAdapterConfig(
        name=name,
        framework=FrameworkType(agent_config.get("framework", "langgraph")),
        description=agent_config.get("description", ""),
        llm_config=llm_config,
        tools=agent_config.get("tools", []),
        system_prompt=agent_config.get("system_prompt"),
        extra_config=agent_config.get("extra_config", {}),
    )


def load_agents_from_settings() -> None:
    """Load agents from Django settings."""
    agents_config = getattr(settings, "AGUI_AGENTS", {})

    for name, config in agents_config.items():
        agent_config = get_agent_config(name)
        if agent_config:
            AgentRegistry.register(name, agent_config)
