"""Usage examples for Django ORM storage backend.

This module demonstrates how to use the Django ORM storage backend
to persist AG-UI protocol data.

Example Usage:
    # In your Django settings
    INSTALLED_APPS = [
        ...
        'django_agui',
    ]

    AGUI = {
        "STORAGE_BACKEND": "django_agui.storage.DjangoStorageBackend",
        # Optional: Enable event storage for debugging
        "ENABLE_EVENT_STORAGE": False,
        # Optional: Enable file storage for media uploads
        "ENABLE_FILE_STORAGE": True,
    }

    # In your code
    from django_agui.storage import DjangoStorageBackend

    storage = DjangoStorageBackend(
        enable_event_storage=False,  # Optional
        enable_file_storage=True     # Optional
    )

    # Initialize
    await storage.initialize()

    # Save a thread
    from django_agui.storage import Thread
    thread = Thread(
        id="thread-123",
        user_id="user-456",
        metadata={"topic": "support"}
    )
    await storage.threads.save_thread(thread)

    # Save a run
    from django_agui.storage import Run
    run = Run(
        id="run-789",
        thread_id="thread-123",
        parent_run_id=None,
        status="running",
        input_data={"messages": [...]},
        output_state=None
    )
    await storage.runs.save_run(run)

    # Save messages
    from django_agui.storage import Message
    message = Message(
        id="msg-001",
        thread_id="thread-123",
        run_id="run-789",
        role="user",
        content="Hello, how can I help?",
        content_type="text"
    )
    await storage.messages.save_message(message)

    # Save a tool call
    from django_agui.storage import ToolCall
    tool_call = ToolCall(
        id="tool-001",
        run_id="run-789",
        message_id="msg-001",
        tool_name="search",
        arguments={"query": "weather"},
        status="completed"
    )
    await storage.tool_calls.save_tool_call(tool_call)

    # List thread messages
    messages = await storage.messages.list_messages(thread_id="thread-123")

    # Close
    await storage.close()
"""

# Data Classes (from base.py)
from django_agui.storage.base import Thread, Run, Message, ToolCall, Event

# Storage Interfaces (from base.py)
from django_agui.storage.base import (
    ThreadStorage,
    RunStorage,
    MessageStorage,
    ToolCallStorage,
    EventStorage,
    FileStorage,
    AGUIStorageBackend,
)

# Django Implementation (from django.py)
from django_agui.storage.django import (
    DjangoThreadStorage,
    DjangoRunStorage,
    DjangoMessageStorage,
    DjangoToolCallStorage,
    DjangoEventStorage,
    DjangoFileStorage,
    DjangoStorageBackend,
)

# Models (from models.py)
from django_agui.models import Thread as ThreadModel
from django_agui.models import Run as RunModel
from django_agui.models import Message as MessageModel
from django_agui.models import ToolCall as ToolCallModel
from django_agui.models import Event as EventModel

__all__ = [
    # Data Classes
    "Thread",
    "Run",
    "Message",
    "ToolCall",
    "Event",
    # Storage Interfaces
    "ThreadStorage",
    "RunStorage",
    "MessageStorage",
    "ToolCallStorage",
    "EventStorage",
    "FileStorage",
    "AGUIStorageBackend",
    # Django Implementations
    "DjangoThreadStorage",
    "DjangoRunStorage",
    "DjangoMessageStorage",
    "DjangoToolCallStorage",
    "DjangoEventStorage",
    "DjangoFileStorage",
    "DjangoStorageBackend",
    # Django Models
    "ThreadModel",
    "RunModel",
    "MessageModel",
    "ToolCallModel",
    "EventModel",
]
