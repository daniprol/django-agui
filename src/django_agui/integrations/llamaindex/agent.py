"""LlamaIndex integration for django-agui."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from ag_ui.core import BaseEvent, RunAgentInput

from django_agui.integrations.base import AgentAdapterConfig, BaseAgentAdapter


class LlamaIndexAgentAdapter(BaseAgentAdapter):
    """Adapter for LlamaIndex agents."""

    def __init__(self, config: AgentAdapterConfig):
        super().__init__(config)
        self._agent = None
        self._workflow = None

    async def initialize(self) -> None:
        """Initialize the LlamaIndex agent."""
        llm = self._create_llm()
        tools = self.config.tools or []

        self._agent = await self._build_agent(llm, tools)

    def _create_llm(self) -> Any:
        """Create the LLM instance based on config."""
        if self.config.llm_config is None:
            raise ValueError("LLM config is required for LlamaIndex adapter")

        provider = self.config.llm_config.provider
        model = self.config.llm_config.model

        if provider.value == "openai":
            from llama_index.llms.openai import OpenAI

            return OpenAI(
                model=model,
                api_key=self.config.llm_config.api_key,
            )
        elif provider.value == "azure_openai":
            from llama_index.llms.azure_openai import AzureOpenAI

            return AzureOpenAI(
                model=model,
                api_key=self.config.llm_config.api_key,
                api_version=self.config.llm_config.api_version or "2024-02-01",
                azure_endpoint=self.config.llm_config.base_url,
                azure_deployment=self.config.llm_config.deployment_name,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def _build_agent(self, llm: Any, tools: list[Any]) -> Any:
        """Build the LlamaIndex agent."""
        from llama_index.core.agent import FunctionCallingAgent
        from llama_index.core.tools import FunctionTool

        llm_tools = []
        for tool in tools:
            if isinstance(tool, FunctionTool):
                llm_tools.append(tool)
            elif callable(tool):
                llm_tools.append(FunctionTool.from_defaults(fn=tool))

        if llm_tools:
            return FunctionCallingAgent.from_tools(
                llm_tools,
                llm=llm,
                system_prompt=self.config.system_prompt
                or "You are a helpful assistant.",
            )
        else:
            from llama_index.core.agent import AgentRunner

            return AgentRunner(
                llm=llm,
                system_prompt=self.config.system_prompt
                or "You are a helpful assistant.",
            )

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

            response = await self._agent.chat(user_message.content)

            message_id = str(uuid.uuid4())
            yield TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                role="assistant",
                message_id=message_id,
            )

            if response.response:
                yield TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=response.response,
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
