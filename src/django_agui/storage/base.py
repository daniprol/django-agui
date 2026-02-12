"""Storage backend abstractions for AG-UI protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Thread:
    """AG-UI conversation thread."""

    id: str
    user_id: str | None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Run:
    """AG-UI agent run."""

    id: str
    thread_id: str
    parent_run_id: str | None
    status: str  # pending, running, completed, failed
    input_data: dict[str, Any]
    output_state: dict[str, Any] | None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


@dataclass
class Message:
    """AG-UI message."""

    id: str
    thread_id: str
    run_id: str | None
    role: str  # user, assistant, system, tool
    content: str
    content_type: str = "text"  # text, binary
    mime_type: str | None = None
    file_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ToolCall:
    """AG-UI tool call."""

    id: str
    run_id: str
    message_id: str | None
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None
    status: str  # pending, running, completed, failed
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


@dataclass
class Event:
    """AG-UI event (for debugging/replay)."""

    id: str
    run_id: str
    event_type: str
    data: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


class ThreadStorage(ABC):
    """Abstract base class for thread storage."""

    @abstractmethod
    async def save_thread(self, thread: Thread) -> None:
        """Save or update a thread."""
        raise NotImplementedError

    @abstractmethod
    async def get_thread(self, thread_id: str) -> Thread | None:
        """Get a thread by ID."""
        raise NotImplementedError

    @abstractmethod
    async def list_threads(
        self, user_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Thread]:
        """List threads, optionally filtered by user."""
        raise NotImplementedError

    @abstractmethod
    async def delete_thread(self, thread_id: str) -> bool:
        """Delete thread and all associated data."""
        raise NotImplementedError


class RunStorage(ABC):
    """Abstract base class for run storage."""

    @abstractmethod
    async def save_run(self, run: Run) -> None:
        """Save or update a run."""
        raise NotImplementedError

    @abstractmethod
    async def get_run(self, run_id: str) -> Run | None:
        """Get a run by ID."""
        raise NotImplementedError

    @abstractmethod
    async def list_runs(
        self, thread_id: str, limit: int = 100, offset: int = 0
    ) -> list[Run]:
        """List runs for a thread."""
        raise NotImplementedError

    @abstractmethod
    async def update_run_status(self, run_id: str, status: str) -> None:
        """Update run status."""
        raise NotImplementedError


class MessageStorage(ABC):
    """Abstract base class for message storage."""

    @abstractmethod
    async def save_message(self, message: Message) -> None:
        """Save a message."""
        raise NotImplementedError

    @abstractmethod
    async def get_message(self, message_id: str) -> Message | None:
        """Get a message by ID."""
        raise NotImplementedError

    @abstractmethod
    async def list_messages(
        self, thread_id: str, limit: int = 1000, offset: int = 0
    ) -> list[Message]:
        """List messages for a thread."""
        raise NotImplementedError

    @abstractmethod
    async def get_thread_messages(
        self, thread_id: str, before_id: str | None = None, limit: int = 1000
    ) -> AsyncIterator[Message]:
        """Stream messages for a thread."""
        raise NotImplementedError


class ToolCallStorage(ABC):
    """Abstract base class for tool call storage."""

    @abstractmethod
    async def save_tool_call(self, tool_call: ToolCall) -> None:
        """Save or update a tool call."""
        raise NotImplementedError

    @abstractmethod
    async def get_tool_call(self, tool_call_id: str) -> ToolCall | None:
        """Get a tool call by ID."""
        raise NotImplementedError

    @abstractmethod
    async def list_tool_calls(
        self, run_id: str, limit: int = 100, offset: int = 0
    ) -> list[ToolCall]:
        """List tool calls for a run."""
        raise NotImplementedError


class EventStorage(ABC):
    """Abstract base class for event storage (optional, for debugging/replay)."""

    @abstractmethod
    async def save_event(self, event: Event) -> None:
        """Save an event."""
        raise NotImplementedError

    @abstractmethod
    async def list_events(
        self, run_id: str, limit: int = 1000, offset: int = 0
    ) -> list[Event]:
        """List events for a run."""
        raise NotImplementedError

    @abstractmethod
    async def get_events_for_run(
        self, run_id: str, after_id: str | None = None
    ) -> AsyncIterator[Event]:
        """Stream events for a run."""
        raise NotImplementedError


class FileStorage(ABC):
    """Abstract base class for file storage."""

    @abstractmethod
    async def save_file(
        self, file_id: str, content: bytes, mime_type: str, filename: str | None = None
    ) -> str:
        """Save a file and return its URL/path."""
        raise NotImplementedError

    @abstractmethod
    async def get_file(self, file_id: str) -> bytes | None:
        """Get file content by ID."""
        raise NotImplementedError

    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file."""
        raise NotImplementedError


class AGUIStorageBackend(ABC):
    """Combined storage backend for all AG-UI entities."""

    def __init__(self) -> None:
        self.threads: ThreadStorage
        self.runs: RunStorage
        self.messages: MessageStorage
        self.tool_calls: ToolCallStorage
        self.events: EventStorage | None = None
        self.files: FileStorage | None = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the storage backend."""
        raise NotImplementedError
