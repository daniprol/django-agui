"""Base abstractions for framework integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from ag_ui.core import BaseEvent, RunAgentInput


class FrameworkType(str, Enum):
    """Supported agent frameworks."""

    LANGGRAPH = "langgraph"
    LLAMAINDEX = "llamaindex"
    AGNO = "agno"


class LLMProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: LLMProviderType
    model: str
    api_key: str | None = None
    base_url: str | None = None
    api_version: str | None = None
    deployment_name: str | None = None
    organization: str | None = None
    extra_kwargs: dict[str, Any] = field(default_factory=dict)

    def get_client_kwargs(self) -> dict[str, Any]:
        """Get kwargs for LLM client initialization."""
        kwargs = {
            "model": self.model,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["base_url"] = self.base_url
        if self.organization:
            kwargs["organization"] = self.organization
        kwargs.update(self.extra_kwargs)
        return kwargs


@dataclass
class AgentAdapterConfig:
    """Configuration for an agent adapter."""

    name: str
    framework: FrameworkType
    description: str = ""
    llm_config: LLMConfig | None = None
    tools: list[Any] = field(default_factory=list)
    system_prompt: str | None = None
    extra_config: dict[str, Any] = field(default_factory=dict)


class BaseAgentAdapter(ABC):
    """Abstract base class for framework agent adapters."""

    def __init__(self, config: AgentAdapterConfig):
        self.config = config
        self._agent = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent with the framework."""
        pass

    @abstractmethod
    async def run(self, input_data: RunAgentInput) -> AsyncIterator[BaseEvent]:
        """Run the agent with input and yield events."""
        pass

    @abstractmethod
    async def get_agent_info(self) -> dict[str, Any]:
        """Get agent metadata."""
        pass

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def framework(self) -> FrameworkType:
        return self.config.framework

    async def cleanup(self) -> None:
        """Cleanup resources. Override if needed."""
        pass
