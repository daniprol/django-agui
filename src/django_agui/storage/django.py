"""Django ORM storage backend implementation for AG-UI protocol."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from django_agui.storage.base import (
    AGUIStorageBackend,
    Event,
    EventStorage,
    FileStorage,
    Message,
    MessageStorage,
    Run,
    RunStorage,
    Thread,
    ThreadStorage,
    ToolCall,
    ToolCallStorage,
)
from django_agui import models as django_models


class DjangoThreadStorage(ThreadStorage):
    """Django ORM thread storage implementation."""

    async def save_thread(self, thread: Thread) -> None:
        """Save or update a thread."""
        await sync_to_async(django_models.Thread.objects.update_or_create)(
            id=thread.id,
            defaults={
                "user_id": thread.user_id,
                "created_at": thread.created_at,
                "updated_at": thread.updated_at,
                "metadata": thread.metadata,
            },
        )

    async def get_thread(self, thread_id: str) -> Thread | None:
        """Get a thread by ID."""
        try:
            django_thread = await sync_to_async(
                django_models.Thread.objects.select_related("user").get
            )(id=thread_id)
            return Thread(
                id=django_thread.id,
                user_id=django_thread.user_id,
                created_at=django_thread.created_at,
                updated_at=django_thread.updated_at,
                metadata=django_thread.metadata,
            )
        except django_models.Thread.DoesNotExist:
            return None

    async def list_threads(
        self, user_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[Thread]:
        """List threads, optionally filtered by user."""
        queryset = django_models.Thread.objects.all()
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        django_threads = await sync_to_async(list)(
            queryset.order_by("-updated_at")[offset : offset + limit]
        )

        return [
            Thread(
                id=t.id,
                user_id=t.user_id,
                created_at=t.created_at,
                updated_at=t.updated_at,
                metadata=t.metadata,
            )
            for t in django_threads
        ]

    async def delete_thread(self, thread_id: str) -> bool:
        """Delete thread and all associated data."""
        try:
            thread = await sync_to_async(django_models.Thread.objects.get)(id=thread_id)
            await sync_to_async(thread.delete)()
            return True
        except django_models.Thread.DoesNotExist:
            return False


class DjangoRunStorage(RunStorage):
    """Django ORM run storage implementation."""

    async def save_run(self, run: Run) -> None:
        """Save or update a run."""
        await sync_to_async(django_models.Run.objects.update_or_create)(
            id=run.id,
            defaults={
                "thread_id": run.thread_id,
                "parent_run_id": run.parent_run_id,
                "status": run.status,
                "input_data": run.input_data,
                "output_state": run.output_state,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
            },
        )

    async def get_run(self, run_id: str) -> Run | None:
        """Get a run by ID."""
        try:
            django_run = await sync_to_async(django_models.Run.objects.get)(id=run_id)
            return Run(
                id=django_run.id,
                thread_id=django_run.thread_id,
                parent_run_id=django_run.parent_run_id,
                status=django_run.status,
                input_data=django_run.input_data,
                output_state=django_run.output_state,
                started_at=django_run.started_at,
                finished_at=django_run.finished_at,
            )
        except django_models.Run.DoesNotExist:
            return None

    async def list_runs(
        self, thread_id: str, limit: int = 100, offset: int = 0
    ) -> list[Run]:
        """List runs for a thread."""
        django_runs = await sync_to_async(list)(
            django_models.Run.objects.filter(thread_id=thread_id).order_by(
                "-started_at"
            )[offset : offset + limit]
        )

        return [
            Run(
                id=r.id,
                thread_id=r.thread_id,
                parent_run_id=r.parent_run_id,
                status=r.status,
                input_data=r.input_data,
                output_state=r.output_state,
                started_at=r.started_at,
                finished_at=r.finished_at,
            )
            for r in django_runs
        ]

    async def update_run_status(self, run_id: str, status: str) -> None:
        """Update run status."""
        finished_at = None
        if status in ("completed", "failed"):
            finished_at = timezone.now()

        await sync_to_async(django_models.Run.objects.filter(id=run_id).update)(
            status=status,
            finished_at=finished_at,
        )


class DjangoMessageStorage(MessageStorage):
    """Django ORM message storage implementation."""

    async def save_message(self, message: Message) -> None:
        """Save a message."""
        await sync_to_async(django_models.Message.objects.create)(
            id=message.id,
            thread_id=message.thread_id,
            run_id=message.run_id,
            role=message.role,
            content=message.content,
            content_type=message.content_type,
            mime_type=message.mime_type,
            file_url=message.file_url or "",
            metadata=message.metadata,
            created_at=message.created_at,
        )

    async def get_message(self, message_id: str) -> Message | None:
        """Get a message by ID."""
        try:
            django_msg = await sync_to_async(django_models.Message.objects.get)(
                id=message_id
            )
            return Message(
                id=django_msg.id,
                thread_id=django_msg.thread_id,
                run_id=django_msg.run_id,
                role=django_msg.role,
                content=django_msg.content,
                content_type=django_msg.content_type,
                mime_type=django_msg.mime_type,
                file_url=django_msg.file_url or None,
                metadata=django_msg.metadata,
                created_at=django_msg.created_at,
            )
        except django_models.Message.DoesNotExist:
            return None

    async def list_messages(
        self, thread_id: str, limit: int = 1000, offset: int = 0
    ) -> list[Message]:
        """List messages for a thread."""
        django_messages = await sync_to_async(list)(
            django_models.Message.objects.filter(thread_id=thread_id).order_by(
                "created_at"
            )[offset : offset + limit]
        )

        return [
            Message(
                id=m.id,
                thread_id=m.thread_id,
                run_id=m.run_id,
                role=m.role,
                content=m.content,
                content_type=m.content_type,
                mime_type=m.mime_type,
                file_url=m.file_url or None,
                metadata=m.metadata,
                created_at=m.created_at,
            )
            for m in django_messages
        ]

    async def get_thread_messages(
        self, thread_id: str, before_id: str | None = None, limit: int = 1000
    ) -> AsyncIterator[Message]:
        """Stream messages for a thread."""
        queryset = django_models.Message.objects.filter(thread_id=thread_id)

        if before_id:
            try:
                before_msg = await sync_to_async(django_models.Message.objects.get)(
                    id=before_id
                )
                queryset = queryset.filter(created_at__lt=before_msg.created_at)
            except django_models.Message.DoesNotExist:
                pass

        django_messages = await sync_to_async(list)(
            queryset.order_by("-created_at")[:limit]
        )

        for django_msg in reversed(django_messages):
            yield Message(
                id=django_msg.id,
                thread_id=django_msg.thread_id,
                run_id=django_msg.run_id,
                role=django_msg.role,
                content=django_msg.content,
                content_type=django_msg.content_type,
                mime_type=django_msg.mime_type,
                file_url=django_msg.file_url or None,
                metadata=django_msg.metadata,
                created_at=django_msg.created_at,
            )


class DjangoToolCallStorage(ToolCallStorage):
    """Django ORM tool call storage implementation."""

    async def save_tool_call(self, tool_call: ToolCall) -> None:
        """Save or update a tool call."""
        await sync_to_async(django_models.ToolCall.objects.update_or_create)(
            id=tool_call.id,
            defaults={
                "run_id": tool_call.run_id,
                "message_id": tool_call.message_id,
                "tool_name": tool_call.tool_name,
                "arguments": tool_call.arguments,
                "result": tool_call.result,
                "status": tool_call.status,
                "started_at": tool_call.started_at,
                "finished_at": tool_call.finished_at,
            },
        )

    async def get_tool_call(self, tool_call_id: str) -> ToolCall | None:
        """Get a tool call by ID."""
        try:
            django_tc = await sync_to_async(django_models.ToolCall.objects.get)(
                id=tool_call_id
            )
            return ToolCall(
                id=django_tc.id,
                run_id=django_tc.run_id,
                message_id=django_tc.message_id,
                tool_name=django_tc.tool_name,
                arguments=django_tc.arguments,
                result=django_tc.result,
                status=django_tc.status,
                started_at=django_tc.started_at,
                finished_at=django_tc.finished_at,
            )
        except django_models.ToolCall.DoesNotExist:
            return None

    async def list_tool_calls(
        self, run_id: str, limit: int = 100, offset: int = 0
    ) -> list[ToolCall]:
        """List tool calls for a run."""
        django_tool_calls = await sync_to_async(list)(
            django_models.ToolCall.objects.filter(run_id=run_id).order_by("started_at")[
                offset : offset + limit
            ]
        )

        return [
            ToolCall(
                id=tc.id,
                run_id=tc.run_id,
                message_id=tc.message_id,
                tool_name=tc.tool_name,
                arguments=tc.arguments,
                result=tc.result,
                status=tc.status,
                started_at=tc.started_at,
                finished_at=tc.finished_at,
            )
            for tc in django_tool_calls
        ]


class DjangoEventStorage(EventStorage):
    """Django ORM event storage implementation."""

    async def save_event(self, event: Event) -> None:
        """Save an event."""
        await sync_to_async(django_models.Event.objects.create)(
            id=event.id,
            run_id=event.run_id,
            event_type=event.event_type,
            data=event.data,
            created_at=event.created_at,
        )

    async def list_events(
        self, run_id: str, limit: int = 1000, offset: int = 0
    ) -> list[Event]:
        """List events for a run."""
        django_events = await sync_to_async(list)(
            django_models.Event.objects.filter(run_id=run_id).order_by("created_at")[
                offset : offset + limit
            ]
        )

        return [
            Event(
                id=e.id,
                run_id=e.run_id,
                event_type=e.event_type,
                data=e.data,
                created_at=e.created_at,
            )
            for e in django_events
        ]

    async def get_events_for_run(
        self, run_id: str, after_id: str | None = None
    ) -> AsyncIterator[Event]:
        """Stream events for a run."""
        queryset = django_models.Event.objects.filter(run_id=run_id)

        if after_id:
            try:
                after_event = await sync_to_async(django_models.Event.objects.get)(
                    id=after_id
                )
                queryset = queryset.filter(created_at__gt=after_event.created_at)
            except django_models.Event.DoesNotExist:
                pass

        django_events = await sync_to_async(list)(queryset.order_by("created_at"))

        for e in django_events:
            yield Event(
                id=e.id,
                run_id=e.run_id,
                event_type=e.event_type,
                data=e.data,
                created_at=e.created_at,
            )


class DjangoFileStorage(FileStorage):
    """Django file storage implementation using MEDIA_ROOT."""

    def __init__(self) -> None:
        self._storage = None

    def _get_storage(self):
        """Lazy load storage to avoid import issues."""
        if self._storage is None:
            from django.core.files.storage import default_storage

            self._storage = default_storage
        return self._storage

    async def save_file(
        self, file_id: str, content: bytes, mime_type: str, filename: str | None = None
    ) -> str:
        """Save a file and return its URL/path."""
        if filename is None:
            filename = file_id

        # Use agui/ subdirectory
        path = f"agui/{file_id}/{filename}"

        content_file = ContentFile(content)
        storage = self._get_storage()

        # Save file
        saved_path = await sync_to_async(storage.save)(path, content_file)

        # Return URL
        return await sync_to_async(storage.url)(saved_path)

    async def get_file(self, file_id: str) -> bytes | None:
        """Get file content by ID."""
        storage = self._get_storage()
        base_path = f"agui/{file_id}"

        @sync_to_async
        def _read_first_file() -> bytes | None:
            try:
                _, files = storage.listdir(base_path)
                if not files:
                    return None
                file_path = f"{base_path}/{files[0]}"
                with storage.open(file_path, "rb") as file_handle:
                    return file_handle.read()
            except Exception:
                return None

        return await _read_first_file()

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file."""
        storage = self._get_storage()
        base_path = f"agui/{file_id}"

        @sync_to_async
        def _delete_all() -> bool:
            try:
                _, files = storage.listdir(base_path)
            except Exception:
                return False

            deleted_any = False
            for filename in files:
                storage.delete(f"{base_path}/{filename}")
                deleted_any = True
            return deleted_any

        return await _delete_all()


class DjangoStorageBackend(AGUIStorageBackend):
    """Complete Django ORM storage backend for AG-UI protocol."""

    def __init__(
        self, enable_event_storage: bool = False, enable_file_storage: bool = True
    ) -> None:
        super().__init__()
        self.threads = DjangoThreadStorage()
        self.runs = DjangoRunStorage()
        self.messages = DjangoMessageStorage()
        self.tool_calls = DjangoToolCallStorage()

        self._enable_event_storage = enable_event_storage
        self._enable_file_storage = enable_file_storage

        if enable_event_storage:
            self.events = DjangoEventStorage()
        else:
            self.events = None

        if enable_file_storage:
            self.files = DjangoFileStorage()
        else:
            self.files = None

    async def initialize(self) -> None:
        """Initialize the storage backend."""
        # Django ORM is initialized automatically
        # Could add checks here for database connectivity
        pass

    async def close(self) -> None:
        """Close the storage backend."""
        # Django ORM connections are managed automatically
        pass

    async def save_conversation_snapshot(
        self, thread_id: str, run_id: str, messages: list[Message]
    ) -> None:
        """Save all messages from a conversation in a transaction."""

        @sync_to_async
        def _save_all():
            with transaction.atomic():
                for message in messages:
                    django_models.Message.objects.create(
                        id=message.id,
                        thread_id=message.thread_id,
                        run_id=message.run_id,
                        role=message.role,
                        content=message.content,
                        content_type=message.content_type,
                        mime_type=message.mime_type,
                        file_url=message.file_url or "",
                        metadata=message.metadata,
                        created_at=message.created_at,
                    )

        await _save_all()
