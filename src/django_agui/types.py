"""Type definitions for django-agui."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from typing import Any, Protocol

from ag_ui.core import BaseEvent, RunAgentInput

AgentRunFunc = Callable[
    [RunAgentInput, Any],
    AsyncIterator[BaseEvent]
    | Awaitable[AsyncIterator[BaseEvent]]
    | Iterable[BaseEvent],
]

EventTranslateFunc = Callable[
    [BaseEvent],
    AsyncIterator[BaseEvent]
    | Awaitable[AsyncIterator[BaseEvent]]
    | Iterable[BaseEvent],
]

GetSystemMessageFunc = Callable[[Any], str | None | Awaitable[str | None]]


class EventEncoder(Protocol):
    """Protocol for event encoders."""

    def encode(self, event: BaseEvent) -> str:
        """Encode an event to string format."""

    def encode_keepalive(self) -> str:
        """Encode a keepalive packet."""


class StateBackend(Protocol):
    """Protocol for state backends."""

    async def save_state(
        self,
        thread_id: str,
        run_id: str,
        state: dict[str, Any],
    ) -> None:
        """Save agent state."""

    async def load_state(self, thread_id: str) -> dict[str, Any] | None:
        """Load agent state."""

    async def delete_state(self, thread_id: str) -> None:
        """Delete agent state."""


class AuthBackend(Protocol):
    """Protocol for authentication backends."""

    def authenticate(self, request: Any) -> Any | None:
        """Authenticate a request. Returns user or ``None``."""

    def check_permission(self, user: Any, agent_path: str) -> bool:
        """Check if a user can access the requested agent path."""
