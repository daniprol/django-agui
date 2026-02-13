"""Unit tests for core AGUI view runtime behavior."""

from __future__ import annotations

import asyncio

import pytest
from django.test.client import AsyncRequestFactory

from ag_ui.core import (
    EventType,
    RunAgentInput,
    TextMessageContentEvent,
    TextMessageStartEvent,
)

from django_agui.views import create_agui_view


class _AuthBackendNone:
    def authenticate(self, request):
        return None

    def check_permission(self, user, agent_path):
        return False


async def _collect_streaming_chunks(response) -> list[str]:
    chunks: list[str] = []
    stream = response.streaming_content
    if hasattr(stream, "__aiter__"):
        async for chunk in stream:
            if isinstance(chunk, bytes):
                chunks.append(chunk.decode("utf-8"))
            else:
                chunks.append(str(chunk))
    else:
        for chunk in stream:
            if isinstance(chunk, bytes):
                chunks.append(chunk.decode("utf-8"))
            else:
                chunks.append(str(chunk))
    return chunks


def _run_input() -> RunAgentInput:
    return RunAgentInput(
        thread_id="thread-1",
        run_id="run-1",
        parent_run_id=None,
        state=None,
        messages=[],
        tools=[],
        context=[],
        forwarded_props=None,
    )


@pytest.mark.asyncio
async def test_view_streams_events(settings):
    """Configured view streams lifecycle and message events."""
    settings.AGUI = {"EMIT_RUN_LIFECYCLE_EVENTS": True}

    async def agent(input_data, request):
        yield TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id="msg-1",
        )
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="hello",
        )

    view = create_agui_view(agent).as_view()
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    assert response.status_code == 200

    payload = "".join(await _collect_streaming_chunks(response))
    assert '"type":"RUN_STARTED"' in payload
    assert '"type":"TEXT_MESSAGE_START"' in payload
    assert '"type":"TEXT_MESSAGE_CONTENT"' in payload
    assert '"type":"RUN_FINISHED"' in payload


@pytest.mark.asyncio
async def test_view_accepts_json_with_charset(settings):
    """JSON requests with charset are accepted."""
    settings.AGUI = {}

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="ok",
        )

    view = create_agui_view(agent).as_view()
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json; charset=utf-8",
    )

    response = await view(request)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_view_rejects_disallowed_origin(settings):
    """CORS disallowed origin is rejected."""
    settings.AGUI = {}

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="ok",
        )

    view = create_agui_view(agent, allowed_origins=["https://allowed.test"]).as_view()
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
        HTTP_ORIGIN="https://blocked.test",
    )

    response = await view(request)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_view_requires_auth_when_enabled(settings):
    """auth_required enforces authentication backend check."""
    settings.AGUI = {"AUTH_BACKEND": f"{__name__}._AuthBackendNone"}

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="ok",
        )

    view = create_agui_view(agent, auth_required=True).as_view()
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_view_run_error_uses_message_field(settings):
    """RUN_ERROR event includes protocol-compliant message field."""
    settings.AGUI = {"ERROR_DETAIL_POLICY": "full"}

    async def agent(input_data, request):
        raise RuntimeError("boom")
        yield  # pragma: no cover

    view = create_agui_view(agent).as_view()
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    payload = "".join(await _collect_streaming_chunks(response))
    assert '"type":"RUN_ERROR"' in payload
    assert '"message":"boom"' in payload
    assert "error_message" not in payload


@pytest.mark.asyncio
async def test_view_timeout_emits_run_error(settings):
    """Stream timeout yields RUN_ERROR with timeout code."""
    settings.AGUI = {
        "SSE_TIMEOUT": 1,
        "SSE_KEEPALIVE_INTERVAL": 0,
        "ERROR_DETAIL_POLICY": "full",
    }

    async def slow_agent(input_data, request):
        await asyncio.sleep(2)
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="too-late",
        )

    view = create_agui_view(slow_agent).as_view()
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    payload = "".join(await _collect_streaming_chunks(response))
    assert '"type":"RUN_ERROR"' in payload
    assert '"code":"timeout"' in payload
