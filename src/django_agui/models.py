"""Django ORM models for AG-UI protocol storage."""

from __future__ import annotations

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid


User = get_user_model()


class Thread(models.Model):
    """AG-UI conversation thread.

    A thread represents a conversation session between a user and an agent.
    It contains multiple runs and messages.
    """

    id = models.CharField(
        primary_key=True,
        max_length=64,
        default=uuid.uuid4,
        help_text="Unique thread identifier",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agui_threads",
        help_text="User who owns this thread",
    )
    created_at = models.DateTimeField(
        default=timezone.now, help_text="When the thread was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When the thread was last updated"
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional thread metadata"
    )

    class Meta:
        db_table = "agui_thread"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Thread({self.id}, user={self.user_id})"


class Run(models.Model):
    """AG-UI agent run.

    A run represents a single agent execution within a thread.
    It contains the input, output state, and status.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=64,
        default=uuid.uuid4,
        help_text="Unique run identifier",
    )
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name="runs",
        help_text="Thread this run belongs to",
    )
    parent_run = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_runs",
        help_text="Parent run for branching/time travel",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Current run status",
    )
    input_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="RunAgentInput data (messages, tools, state, etc.)",
    )
    output_state = models.JSONField(
        null=True, blank=True, help_text="Final state after run completion"
    )
    started_at = models.DateTimeField(
        default=timezone.now, help_text="When the run started"
    )
    finished_at = models.DateTimeField(
        null=True, blank=True, help_text="When the run finished"
    )

    class Meta:
        db_table = "agui_run"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["thread", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
            models.Index(fields=["parent_run"]),
        ]

    def __str__(self) -> str:
        return f"Run({self.id}, thread={self.thread_id}, status={self.status})"


class Message(models.Model):
    """AG-UI message.

    A message represents a single communication in a thread.
    Can be text or binary (image, audio, file).
    """

    CONTENT_TYPE_CHOICES = [
        ("text", "Text"),
        ("binary", "Binary"),
    ]

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
        ("tool", "Tool"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=64,
        default=uuid.uuid4,
        help_text="Unique message identifier",
    )
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text="Thread this message belongs to",
    )
    run = models.ForeignKey(
        Run,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="messages",
        help_text="Run this message belongs to",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Sender role (user, assistant, system, tool)",
    )
    content = models.TextField(help_text="Message content (text or base64 for binary)")
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default="text",
        help_text="Content type (text or binary)",
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="MIME type for binary content (e.g., image/png, application/pdf)",
    )
    file = models.FileField(
        upload_to="agui/%Y/%m/%d/",
        null=True,
        blank=True,
        help_text="File attachment (for binary content)",
    )
    file_url = models.URLField(
        max_length=500, blank=True, help_text="External URL for large files"
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional message metadata"
    )
    created_at = models.DateTimeField(
        default=timezone.now, help_text="When the message was created"
    )

    class Meta:
        db_table = "agui_message"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["run", "created_at"]),
            models.Index(fields=["role", "created_at"]),
        ]

    def __str__(self) -> str:
        content_preview = self.content[:50] if len(self.content) > 50 else self.content
        return f"Message({self.id}, role={self.role}, content={content_preview!r})"


class ToolCall(models.Model):
    """AG-UI tool call.

    Represents a tool invocation by the agent.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=64,
        default=uuid.uuid4,
        help_text="Unique tool call identifier",
    )
    run = models.ForeignKey(
        Run,
        on_delete=models.CASCADE,
        related_name="tool_calls",
        help_text="Run this tool call belongs to",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tool_calls",
        help_text="Message containing this tool call",
    )
    tool_name = models.CharField(
        max_length=200, help_text="Name of the tool being called"
    )
    arguments = models.JSONField(default=dict, blank=True, help_text="Tool arguments")
    result = models.JSONField(null=True, blank=True, help_text="Tool execution result")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Current tool call status",
    )
    started_at = models.DateTimeField(
        default=timezone.now, help_text="When the tool call started"
    )
    finished_at = models.DateTimeField(
        null=True, blank=True, help_text="When the tool call finished"
    )

    class Meta:
        db_table = "agui_tool_call"
        ordering = ["started_at"]
        indexes = [
            models.Index(fields=["run", "started_at"]),
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self) -> str:
        return f"ToolCall({self.id}, tool={self.tool_name}, status={self.status})"


class Event(models.Model):
    """AG-UI event for debugging/replay.

    Stores raw events for debugging, replay, or audit purposes.
    Optional - can be disabled to save storage.
    """

    id = models.CharField(
        primary_key=True,
        max_length=64,
        default=uuid.uuid4,
        help_text="Unique event identifier",
    )
    run = models.ForeignKey(
        Run,
        on_delete=models.CASCADE,
        related_name="events",
        help_text="Run this event belongs to",
    )
    event_type = models.CharField(
        max_length=50,
        help_text="AG-UI event type (e.g., TEXT_MESSAGE_START, TOOL_CALL_END)",
    )
    data = models.JSONField(default=dict, blank=True, help_text="Event data payload")
    created_at = models.DateTimeField(
        default=timezone.now, help_text="When the event was created"
    )

    class Meta:
        db_table = "agui_event"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["run", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Event({self.id}, type={self.event_type})"
