"""LangGraph integration for django-agui."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from ag_ui.core import BaseEvent, RunAgentInput
from ag_ui.encoder import EventEncoder

from django_agui.integrations.base import AgentAdapterConfig, BaseAgentAdapter


class LangGraphAgentAdapter(BaseAgentAdapter):
    """Adapter for LangGraph agents."""

    def __init__(self, config: AgentAdapterConfig):
        super().__init__(config)
        self._graph = None
        self._langgraph_agent = None

    async def initialize(self) -> None:
        """Initialize the LangGraph agent."""
        from ag_ui_langgraph import LangGraphAgent

        graph = self._build_graph()
        self._langgraph_agent = LangGraphAgent(
            name=self.config.name,
            graph=graph,
            description=self.config.description,
            config=self.config.extra_config.get("langgraph_config"),
        )

    def _build_graph(self) -> Any:
        """Build the LangGraph state graph."""
        from langgraph.graph import StateGraph, END
        from langgraph.prebuilt import create_react_agent

        llm = self._create_llm()
        tools = self.config.tools or []

        if tools:
            graph = create_react_agent(
                llm, tools=tools, state_schema=self._get_state_schema()
            )
        else:
            graph = self._create_simple_graph(llm)

        return graph

    def _get_state_schema(self) -> type:
        """Get the state schema for the graph."""
        from typing import TypedDict

        class AgentState(TypedDict):
            messages: list

        return AgentState

    def _create_simple_graph(self, llm: Any) -> Any:
        """Create a simple chat graph without tools."""
        from langgraph.graph import StateGraph, END, START

        schema = self._get_state_schema()

        def should_continue(state: dict) -> str:
            return END

        workflow = StateGraph(schema)
        workflow.add_node("agent", self._create_agent_node(llm))
        workflow.set_entry_point(START)
        workflow.add_edge(START, "agent")
        workflow.add_edge("agent", END)

        return workflow.compile()

    def _create_agent_node(self, llm: Any):
        """Create an agent node for the graph."""

        def agent_node(state: dict) -> dict:
            from langchain_core.messages import HumanMessage

            messages = state.get("messages", [])
            response = llm.invoke(messages)
            return {"messages": [response]}

        return agent_node

    def _create_llm(self) -> Any:
        """Create the LLM instance based on config."""
        if self.config.llm_config is None:
            raise ValueError("LLM config is required for LangGraph adapter")

        provider = self.config.llm_config.provider
        model = self.config.llm_config.model
        kwargs = self.config.llm_config.get_client_kwargs()

        if provider.value == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(**kwargs)
        elif provider.value == "azure_openai":
            from langchain_openai import AzureChatOpenAI

            azure_kwargs = {
                "azure_deployment": self.config.llm_config.deployment_name or model,
                "api_version": self.config.llm_config.api_version or "2024-02-01",
            }
            if self.config.llm_config.base_url:
                azure_kwargs["azure_endpoint"] = self.config.llm_config.base_url
            if self.config.llm_config.api_key:
                azure_kwargs["api_key"] = self.config.llm_config.api_key

            return AzureChatOpenAI(**azure_kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def run(self, input_data: RunAgentInput) -> AsyncIterator[BaseEvent]:
        """Run the agent with input and yield events."""
        if self._langgraph_agent is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        thread_id = input_data.thread_id or str(uuid.uuid4())
        run_id = input_data.run_id or str(uuid.uuid4())

        modified_input = input_data.copy(
            update={"thread_id": thread_id, "run_id": run_id}
        )

        encoder = EventEncoder(accept="text/event-stream")

        async for event_str in self._langgraph_agent.run(modified_input):
            try:
                event_data = self._parse_sse_event(event_str)
                if event_data:
                    yield event_data
            except Exception:
                pass

    def _parse_sse_event(self, event_str: str) -> BaseEvent | None:
        """Parse SSE event string into BaseEvent."""
        if not event_str or ":" not in event_str:
            return None

        parts = event_str.split(":", 1)
        if len(parts) != 2:
            return None

        prefix, data = parts
        if prefix.strip() != "data":
            return None

        import json

        try:
            data_dict = json.loads(data.strip())
            return self._dict_to_event(data_dict)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _dict_to_event(self, data: dict) -> BaseEvent:
        """Convert dictionary to appropriate event type."""
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
            StateSnapshotEvent,
            CustomEvent,
            RawEvent,
        )

        event_type = data.get("type")
        event_class = {
            EventType.RUN_STARTED: RunStartedEvent,
            EventType.RUN_FINISHED: RunFinishedEvent,
            EventType.RUN_ERROR: RunErrorEvent,
            EventType.TEXT_MESSAGE_START: TextMessageStartEvent,
            EventType.TEXT_MESSAGE_CONTENT: TextMessageContentEvent,
            EventType.TEXT_MESSAGE_END: TextMessageEndEvent,
            EventType.TOOL_CALL_START: ToolCallStartEvent,
            EventType.TOOL_CALL_ARGS: ToolCallArgsEvent,
            EventType.TOOL_CALL_END: ToolCallEndEvent,
            EventType.TOOL_CALL_RESULT: ToolCallResultEvent,
            EventType.STATE_SNAPSHOT: StateSnapshotEvent,
            EventType.CUSTOM: CustomEvent,
            EventType.RAW: RawEvent,
        }.get(event_type)

        if event_class:
            return event_class(**data)
        return RawEvent(type=EventType.RAW, event=data)

    async def get_agent_info(self) -> dict[str, Any]:
        """Get agent metadata."""
        return {
            "name": self.config.name,
            "framework": self.config.framework.value,
            "description": self.config.description,
            "model": self.config.llm_config.model if self.config.llm_config else None,
            "tools_count": len(self.config.tools),
        }
