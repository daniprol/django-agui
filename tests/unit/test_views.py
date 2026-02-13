"""Unit tests for core AGUI view runtime behavior."""

from __future__ import annotations

import asyncio

from ag_ui.core import (
    EventType,
    RunAgentInput,
    StateSnapshotEvent,
    TextMessageContentEvent,
    TextMessageStartEvent,
)
from django.test.client import AsyncRequestFactory
import pytest

from django_agui.views import AGUIView


class _AuthBackendNone:
    def authenticate(self, request):
        return None

    def check_permission(self, user, agent_path):
        return False


class _StateBackendRecorder:
    saved: list[tuple[str, str, object]] = []
    deleted: list[str] = []

    @classmethod
    def reset(cls):
        cls.saved = []
        cls.deleted = []

    async def save_state(self, thread_id, run_id, state):
        type(self).saved.append((thread_id, run_id, state))

    async def load_state(self, thread_id):
        return None

    async def delete_state(self, thread_id):
        type(self).deleted.append(thread_id)


class _StateBackendNoDelete:
    saved: list[tuple[str, str, object]] = []

    @classmethod
    def reset(cls):
        cls.saved = []

    async def save_state(self, thread_id, run_id, state):
        type(self).saved.append((thread_id, run_id, state))

    async def load_state(self, thread_id):
        return None


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

    view = AGUIView.as_view(run_agent=agent)
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

    view = AGUIView.as_view(run_agent=agent)
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

    view = AGUIView.as_view(run_agent=agent, allowed_origins=["https://allowed.test"])
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

    view = AGUIView.as_view(run_agent=agent, auth_required=True)
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

    view = AGUIView.as_view(run_agent=agent)
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

    view = AGUIView.as_view(run_agent=slow_agent)
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


@pytest.mark.asyncio
async def test_view_keepalive_does_not_cancel_slow_agent(settings):
    """Keepalive packets should not cancel a still-running agent iterator."""
    settings.AGUI = {
        "SSE_TIMEOUT": 0,
        "SSE_KEEPALIVE_INTERVAL": 1,
    }

    async def slow_agent(input_data, request):
        await asyncio.sleep(1.1)
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="event-after-keepalive",
        )

    view = AGUIView.as_view(run_agent=slow_agent)
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    payload = "".join(await _collect_streaming_chunks(response))
    assert ": keepalive" in payload
    assert '"type":"TEXT_MESSAGE_CONTENT"' in payload
    assert "event-after-keepalive" in payload


@pytest.mark.asyncio
async def test_view_auto_error_policy_uses_debug_setting(settings):
    """Auto policy exposes details in DEBUG mode."""
    settings.DEBUG = True
    settings.AGUI = {"ERROR_DETAIL_POLICY": "auto"}

    async def agent(input_data, request):
        raise RuntimeError("debug-boom")
        yield  # pragma: no cover

    view = AGUIView.as_view(run_agent=agent)
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    payload = "".join(await _collect_streaming_chunks(response))
    assert '"message":"debug-boom"' in payload


@pytest.mark.asyncio
async def test_view_state_save_policy_disabled(settings):
    """Disabled policy skips state backend writes."""
    _StateBackendRecorder.reset()
    settings.AGUI = {
        "STATE_BACKEND": f"{__name__}._StateBackendRecorder",
        "STATE_SAVE_POLICY": "disabled",
    }

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="ok",
        )

    view = AGUIView.as_view(run_agent=agent)
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    assert response.status_code == 200
    await _collect_streaming_chunks(response)
    assert _StateBackendRecorder.saved == []
    assert _StateBackendRecorder.deleted == []


@pytest.mark.asyncio
async def test_view_state_save_policy_on_snapshot(settings):
    """on_snapshot policy only persists snapshot state values."""
    _StateBackendRecorder.reset()
    settings.AGUI = {
        "STATE_BACKEND": f"{__name__}._StateBackendRecorder",
        "STATE_SAVE_POLICY": "on_snapshot",
    }

    async def agent(input_data, request):
        yield StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={"foo": "bar"},
        )

    view = AGUIView.as_view(run_agent=agent)
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    assert response.status_code == 200
    await _collect_streaming_chunks(response)
    assert _StateBackendRecorder.saved == [("thread-1", "run-1", {"foo": "bar"})]


@pytest.mark.asyncio
async def test_view_state_none_is_not_saved_without_delete_method(settings):
    """`None` state should not be written when backend has no delete_state."""
    _StateBackendNoDelete.reset()
    settings.AGUI = {
        "STATE_BACKEND": f"{__name__}._StateBackendNoDelete",
        "STATE_SAVE_POLICY": "always",
    }

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="ok",
        )

    view = AGUIView.as_view(run_agent=agent)
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    assert response.status_code == 200
    await _collect_streaming_chunks(response)
    assert _StateBackendNoDelete.saved == []


@pytest.mark.asyncio
async def test_view_options_does_not_require_auth(settings):
    """CORS preflight should work even when global auth is required."""
    settings.AGUI = {
        "REQUIRE_AUTHENTICATION": True,
        "AUTH_BACKEND": f"{__name__}._AuthBackendNone",
        "ALLOWED_ORIGINS": ["https://app.test"],
    }

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="ok",
        )

    view = AGUIView.as_view(run_agent=agent)
    factory = AsyncRequestFactory()
    request = factory.options(
        "/agent/",
        HTTP_ORIGIN="https://app.test",
    )

    response = await view(request)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_view_error_response_includes_cors_headers(settings):
    """Request validation errors should still include CORS headers."""
    settings.AGUI = {
        "ALLOWED_ORIGINS": ["https://app.test"],
    }

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="ok",
        )

    view = AGUIView.as_view(run_agent=agent)
    factory = AsyncRequestFactory()
    request = factory.post(
        "/agent/",
        data="not-json",
        content_type="text/plain",
        HTTP_ORIGIN="https://app.test",
    )

    response = await view(request)
    assert response.status_code == 400
    assert response["Access-Control-Allow-Origin"] == "https://app.test"


@pytest.mark.asyncio
async def test_unconfigured_view_returns_500(settings):
    """Missing run_agent should be treated as server misconfiguration."""
    settings.AGUI = {}

    view = AGUIView.as_view()
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
    )

    response = await view(request)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_invalid_allowed_origins_returns_500(settings):
    """Misconfigured ALLOWED_ORIGINS should fail with a controlled 500."""
    settings.AGUI = {
        "ALLOWED_ORIGINS": "https://app.test",
    }

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="ok",
        )

    view = AGUIView.as_view(run_agent=agent)
    factory = AsyncRequestFactory()
    request = factory.generic(
        "POST",
        "/agent/",
        data=_run_input().model_dump_json(by_alias=True),
        content_type="application/json",
        HTTP_ORIGIN="https://app.test",
    )

    response = await view(request)
    assert response.status_code == 500
