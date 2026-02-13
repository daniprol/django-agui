"""Agno integration for django-agui."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from ag_ui.core import BaseEvent, RunAgentInput

from django_agui.integrations.base import AgentAdapterConfig, BaseAgentAdapter


class AgnoAgentAdapter(BaseAgentAdapter):
    """Adapter for Agno agents."""

    def __init__(self, config: AgentAdapterConfig):
        super().__init__(config)
        self._agent = None

    async def initialize(self) -> None:
        """Initialize the Agno agent."""
        agent = self._create_agent()
        self._agent = agent

    def _create_llm(self) -> Any:
        """Create the LLM instance based on config."""
        if self.config.llm_config is None:
            raise ValueError("LLM config is required for Agno adapter")

        provider = self.config.llm_config.provider
        model = self.config.llm_config.model

        if provider.value == "openai":
            from agno.models.openai import OpenAIChat

            return OpenAIChat(
                id=model,
                api_key=self.config.llm_config.api_key,
            )
        elif provider.value == "azure_openai":
            from agno.models.azure import AzureOpenAI

            return AzureOpenAI(
                id=model,
                api_key=self.config.llm_config.api_key,
                api_version=self.config.llm_config.api_version or "2024-02-01",
                azure_endpoint=self.config.llm_config.base_url,
                azure_deployment=self.config.llm_config.deployment_name,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _create_agent(self) -> Any:
        """Create the Agno agent."""
        from agno import Agent

        llm = self._create_llm()
        tools = self.config.tools or []

        agent = Agent(
            model=llm,
            name=self.config.name,
            description=self.config.description or "An AI assistant",
            tools=tools,
            markdown=True,
        )

        return agent

    async def run(self, input_data: RunAgentInput) -> AsyncIterator[BaseEvent]:
        """Run the agent with input and yield events."""
        if self._agent is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        from ag_ui.core import (
            EventType,
            RunStartedEvent,
            RunFinishedEvent,
            RunErrorEvent,
            TextMessageStartEvent,
            TextMessageContentEvent,
            TextMessageEndEvent,
            ToolCallStartEvent,
            ToolCallArgsEvent,
            ToolCallEndEvent,
            ToolCallResultEvent,
        )

        thread_id = input_data.thread_id or str(uuid.uuid4())
        run_id = input_data.run_id or str(uuid.uuid4())

        yield RunStartedEvent(
            type=EventType.RUN_STARTED, thread_id=thread_id, run_id=run_id
        )

        try:
            messages = input_data.messages or []
            user_message = messages[-1] if messages else None

            if user_message is None:
                raise ValueError("No message provided")

            response = self._agent.chat(user_message.content)

            message_id = str(uuid.uuid4())
            yield TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                role="assistant",
                message_id=message_id,
            )

            if response.content:
                yield TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=response.content,
                )

            yield TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id,
            )

            yield RunFinishedEvent(
                type=EventType.RUN_FINISHED, thread_id=thread_id, run_id=run_id
            )

        except Exception as e:
            yield RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=str(e),
                raw_event={"error": str(e)},
            )

    async def get_agent_info(self) -> dict[str, Any]:
        """Get agent metadata."""
        return {
            "name": self.config.name,
            "framework": self.config.framework.value,
            "description": self.config.description,
            "model": self.config.llm_config.model if self.config.llm_config else None,
            "tools_count": len(self.config.tools),
        }
