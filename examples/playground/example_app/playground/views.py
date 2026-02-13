"""API views for the playground."""

import uuid
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

USE_DB_STORAGE = getattr(settings, "AGUI", {}).get("USE_DB_STORAGE", False)

in_memory_threads: dict[str, dict[str, Any]] = {}


@api_view(["GET"])
def playground_config(request: Request) -> Response:
    """Get playground configuration."""
    return Response(
        {
            "use_db_storage": USE_DB_STORAGE,
            "has_agents": True,
        }
    )


@api_view(["GET", "POST"])
def threads_list(request: Request) -> Response:
    """List or create threads."""
    if request.method == "GET":
        if USE_DB_STORAGE:
            return get_db_threads(request)
        return get_in_memory_threads(request)

    if request.method == "POST":
        if USE_DB_STORAGE:
            return create_db_thread(request)
        return create_in_memory_thread(request)


def get_in_memory_threads(request: Request) -> Response:
    """Get in-memory threads."""
    threads = [
        {
            "id": tid,
            "agent_name": data.get("agent_name", ""),
            "title": data.get("title", "New conversation"),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
        }
        for tid, data in in_memory_threads.items()
    ]
    return Response({"threads": threads})


def create_in_memory_thread(request: Request) -> Response:
    """Create an in-memory thread."""
    agent_name = request.data.get("agent_name", "")
    thread_id = str(uuid.uuid4())
    now = "2024-01-01T00:00:00Z"

    in_memory_threads[thread_id] = {
        "id": thread_id,
        "agent_name": agent_name,
        "title": "New conversation",
        "created_at": now,
        "updated_at": now,
    }

    return Response(
        {
            "id": thread_id,
            "agent_name": agent_name,
            "title": "New conversation",
            "created_at": now,
            "updated_at": now,
        },
        status=status.HTTP_201_CREATED,
    )


def get_db_threads(request: Request) -> Response:
    """Get threads from database."""
    try:
        from django_agui.models import Thread as DBThread

        threads = DBThread.objects.all().order_by("-updated_at")[:50]
        return Response(
            {
                "threads": [
                    {
                        "id": str(t.id),
                        "agent_name": t.agent_name or "",
                        "title": t.title or "New conversation",
                        "created_at": t.created_at.isoformat() if t.created_at else "",
                        "updated_at": t.updated_at.isoformat() if t.updated_at else "",
                    }
                    for t in threads
                ]
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def create_db_thread(request: Request) -> Response:
    """Create a thread in database."""
    try:
        from django_agui.models import Thread as DBThread

        agent_name = request.data.get("agent_name", "")
        thread = DBThread.objects.create(
            agent_name=agent_name,
            title="New conversation",
        )

        return Response(
            {
                "id": str(thread.id),
                "agent_name": thread.agent_name or "",
                "title": thread.title or "New conversation",
                "created_at": thread.created_at.isoformat()
                if thread.created_at
                else "",
                "updated_at": thread.updated_at.isoformat()
                if thread.updated_at
                else "",
            },
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET", "DELETE"])
def thread_detail(request: Request, thread_id: str) -> Response:
    """Get or delete a specific thread."""
    if request.method == "GET":
        if USE_DB_STORAGE:
            return get_db_thread(request, thread_id)
        return get_in_memory_thread(request, thread_id)

    if request.method == "DELETE":
        if USE_DB_STORAGE:
            return delete_db_thread(request, thread_id)
        return delete_in_memory_thread(request, thread_id)


def get_in_memory_thread(request: Request, thread_id: str) -> Response:
    """Get an in-memory thread."""
    thread = in_memory_threads.get(thread_id)
    if not thread:
        return Response({"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(
        {
            "id": thread["id"],
            "agent_name": thread.get("agent_name", ""),
            "title": thread.get("title", "New conversation"),
            "created_at": thread.get("created_at", ""),
            "updated_at": thread.get("updated_at", ""),
        }
    )


def delete_in_memory_thread(request: Request, thread_id: str) -> Response:
    """Delete an in-memory thread."""
    if thread_id in in_memory_threads:
        del in_memory_threads[thread_id]
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND)


def get_db_thread(request: Request, thread_id: str) -> Response:
    """Get a thread from database."""
    try:
        from django_agui.models import Thread as DBThread

        thread = DBThread.objects.get(id=thread_id)
        return Response(
            {
                "id": str(thread.id),
                "agent_name": thread.agent_name or "",
                "title": thread.title or "New conversation",
                "created_at": thread.created_at.isoformat()
                if thread.created_at
                else "",
                "updated_at": thread.updated_at.isoformat()
                if thread.updated_at
                else "",
            }
        )
    except DBThread.DoesNotExist:
        return Response({"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def delete_db_thread(request: Request, thread_id: str) -> Response:
    """Delete a thread from database."""
    try:
        from django_agui.models import Thread as DBThread

        thread = DBThread.objects.get(id=thread_id)
        thread.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except DBThread.DoesNotExist:
        return Response({"error": "Thread not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
