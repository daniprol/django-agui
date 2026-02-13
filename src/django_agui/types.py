"""Type definitions for django-agui."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from typing import Any, Protocol, TypeVar

from ag_ui.core import BaseEvent, RunAgentInput


AgentRunFunc = Callable[
    [RunAgentInput, Any],
    AsyncIterator[BaseEvent] | Awaitable[AsyncIterator[BaseEvent]],
]

EventTranslateFunc = Callable[
    [Any],
    AsyncIterator[BaseEvent],
]

GetSystemMessageFunc = Callable[[Any], str | None]

T = TypeVar("T")


class EventEncoder(Protocol):
    """Protocol for event encoders."""

    def encode(self, event: BaseEvent) -> str:
        """Encode an event to string format."""
        ...


class StateBackend(Protocol):
    """Protocol for state backends."""

    async def save_state(
        self, thread_id: str, run_id: str, state: dict[str, Any]
    ) -> None:
        """Save agent state."""
        ...

    async def load_state(self, thread_id: str) -> dict[str, Any] | None:
        """Load agent state."""
        ...

    async def delete_state(self, thread_id: str) -> None:
        """Delete agent state."""
        ...


class AuthBackend(Protocol):
    """Protocol for authentication backends."""

    def authenticate(self, request: Any) -> Any | None:
        """Authenticate a request. Returns user or None."""
        ...

    def check_permission(self, user: Any, agent_path: str) -> bool:
        """Check if user has permission for the agent."""
        ...


class AgentMetadata:
    """Metadata for an agent endpoint."""

    def __init__(
        self,
        path: str,
        run_agent: AgentRunFunc,
        translate_event: EventTranslateFunc | None = None,
        get_system_message: GetSystemMessageFunc | None = None,
        auth_required: bool = False,
        allowed_origins: list[str] | None = None,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
    ) -> None:
        self.path = path
        self.run_agent = run_agent
        self.translate_event = translate_event
        self.get_system_message = get_system_message
        self.auth_required = auth_required
        self.allowed_origins = allowed_origins
        self.emit_run_lifecycle_events = emit_run_lifecycle_events
        self.error_detail_policy = error_detail_policy
        self.state_save_policy = state_save_policy
