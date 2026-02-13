"""Shared runtime utilities for AG-UI request handling and streaming."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from contextlib import suppress
from dataclasses import dataclass
import inspect
import json
import logging
from typing import Any, Protocol

from ag_ui.core import (
    BaseEvent,
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StateSnapshotEvent,
    SystemMessage,
)
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

from django_agui.encoders import SSEEventEncoder
from django_agui.settings import get_backend_class, get_setting

logger = logging.getLogger(__name__)


class StreamEncoder(Protocol):
    """Protocol for event encoder implementations."""

    def encode(self, event: BaseEvent) -> str:
        """Encode an AG-UI event for transport."""
        ...

    def encode_keepalive(self) -> str:
        """Encode a keepalive packet."""
        ...


@dataclass(slots=True)
class AuthResult:
    """Authentication/authorization result."""

    allowed: bool
    status_code: int | None = None
    message: str | None = None
    user: Any = None


@dataclass(slots=True)
class AGUIRequestError(Exception):
    """Request validation/authorization error."""

    status_code: int
    message: str


@dataclass(slots=True)
class AGUIExecutionConfig:
    """Execution options resolved from settings and per-view overrides."""

    keepalive_interval: int
    timeout: int
    emit_run_lifecycle_events: bool
    error_detail_policy: str
    state_save_policy: str

    @classmethod
    def from_settings(
        cls,
        *,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
    ) -> AGUIExecutionConfig:
        """Build execution config from settings with optional overrides."""
        resolved_emit = (
            bool(get_setting("EMIT_RUN_LIFECYCLE_EVENTS", True))
            if emit_run_lifecycle_events is None
            else emit_run_lifecycle_events
        )
        resolved_error_policy = resolve_error_policy(error_detail_policy)
        resolved_state_policy = resolve_state_save_policy(state_save_policy)

        return cls(
            keepalive_interval=int(get_setting("SSE_KEEPALIVE_INTERVAL", 30) or 0),
            timeout=int(get_setting("SSE_TIMEOUT", 300) or 0),
            emit_run_lifecycle_events=resolved_emit,
            error_detail_policy=resolved_error_policy,
            state_save_policy=resolved_state_policy,
        )


@dataclass(slots=True)
class AGUICollectedRun:
    """Result of non-streaming execution."""

    thread_id: str
    run_id: str
    events: list[BaseEvent]
    has_error: bool = False


def _is_debug_mode() -> bool:
    return bool(get_setting("DEBUG", False) or getattr(django_settings, "DEBUG", False))


def resolve_error_policy(policy: str | None) -> str:
    """Resolve runtime error detail policy.

    Returns:
        "safe" or "full"
    """
    configured = policy or str(get_setting("ERROR_DETAIL_POLICY", "auto"))
    if configured == "auto":
        return "full" if _is_debug_mode() else "safe"
    if configured in {"safe", "full"}:
        return configured
    raise ImproperlyConfigured(
        'AGUI.ERROR_DETAIL_POLICY must be one of: "auto", "safe", "full"'
    )


def resolve_state_save_policy(policy: str | None) -> str:
    """Resolve state persistence policy."""
    configured = policy or str(get_setting("STATE_SAVE_POLICY", "always"))
    if configured not in {"always", "on_snapshot", "disabled"}:
        raise ImproperlyConfigured(
            'AGUI.STATE_SAVE_POLICY must be one of: "always", "on_snapshot", "disabled"'
        )
    return configured


def is_json_content_type(content_type: str | None) -> bool:
    """Return True when request Content-Type is JSON (charset allowed)."""
    if not content_type:
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json"


def ensure_json_content_type(content_type: str | None) -> None:
    """Validate JSON request content type."""
    if not is_json_content_type(content_type):
        raise AGUIRequestError(400, "Content-Type must be application/json")


def get_request_header(request: Any, key: str) -> str | None:
    """Get a request header in a framework-agnostic way."""
    wanted = key.lower()
    if hasattr(request, "headers"):
        direct = request.headers.get(key)
        if direct is not None:
            return direct
        for header_key, value in request.headers.items():
            normalized = str(header_key).lower()
            if normalized == wanted or normalized == f"http-{wanted}":
                return str(value)

    meta = getattr(request, "META", {})
    normalized = key.upper().replace("-", "_")
    return (
        meta.get(f"HTTP_{normalized}")
        or meta.get(normalized)
        or meta.get(f"HTTP_HTTP_{normalized}")
    )


def get_request_origin(request: Any) -> str | None:
    """Get Origin header from a request."""
    return get_request_header(request, "Origin")


def resolve_allowed_origins(allowed_origins: list[str] | None) -> list[str] | None:
    """Resolve allowed origins from view overrides or global settings."""
    raw_origins = allowed_origins
    if raw_origins is None:
        raw_origins = get_setting("ALLOWED_ORIGINS")

    if raw_origins is None:
        return None

    if not isinstance(raw_origins, (list, tuple)):
        raise ImproperlyConfigured("AGUI.ALLOWED_ORIGINS must be a list or tuple")

    return [str(origin) for origin in raw_origins]


def is_origin_allowed(origin: str | None, allowed_origins: list[str] | None) -> bool:
    """Check whether request origin is allowed."""
    if allowed_origins is None:
        return True
    if origin is None:
        return True
    if "*" in allowed_origins:
        return True
    return origin in allowed_origins


def enforce_origin_and_auth(
    request: Any,
    *,
    auth_required: bool = False,
    allowed_origins: list[str] | None = None,
) -> tuple[str | None, list[str] | None]:
    """Validate CORS origin and authentication/authorization."""
    origin = get_request_origin(request)
    resolved_origins = resolve_allowed_origins(allowed_origins)

    if not is_origin_allowed(origin, resolved_origins):
        raise AGUIRequestError(403, "Origin not allowed")

    auth = authenticate_request(request, auth_required=auth_required)
    if not auth.allowed:
        raise AGUIRequestError(auth.status_code or 401, auth.message or "Unauthorized")

    return origin, resolved_origins


def get_cors_headers(
    origin: str | None,
    allowed_origins: list[str] | None,
) -> dict[str, str]:
    """Build CORS headers for a response."""
    if origin is None or allowed_origins is None:
        return {}
    if not is_origin_allowed(origin, allowed_origins):
        return {}

    headers: dict[str, str]
    if "*" in allowed_origins:
        headers = {"Access-Control-Allow-Origin": "*"}
    else:
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Vary": "Origin",
        }

    headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return headers


def enforce_max_content_length(request: Any) -> None:
    """Validate request payload against configured max size."""
    max_content_length = get_setting("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)
    if max_content_length is None:
        return

    content_length = get_request_header(request, "Content-Length")
    if not content_length:
        return

    try:
        if int(content_length) > int(max_content_length):
            raise AGUIRequestError(413, "Payload too large")
    except ValueError:
        return


def parse_run_input_json(body: Any) -> RunAgentInput:
    """Parse and validate JSON AG-UI request body."""
    try:
        return RunAgentInput.model_validate_json(body)
    except json.JSONDecodeError as exc:
        raise AGUIRequestError(400, f"Invalid JSON: {exc}") from exc
    except Exception as exc:
        raise AGUIRequestError(400, f"Invalid request: {exc}") from exc


def parse_run_input_payload(payload: Any) -> RunAgentInput:
    """Parse and validate Python object AG-UI payload."""
    try:
        return RunAgentInput.model_validate(payload)
    except Exception as exc:
        raise AGUIRequestError(400, f"Invalid request: {exc}") from exc


def build_event_encoder() -> StreamEncoder:
    """Build event encoder from settings."""
    encoder_cls = get_backend_class("EVENT_ENCODER")
    if encoder_cls is None:
        return SSEEventEncoder()

    encoder = encoder_cls()
    if not hasattr(encoder, "encode"):
        raise ImproperlyConfigured(
            "EVENT_ENCODER must implement an encode(event) method"
        )
    if not hasattr(encoder, "encode_keepalive"):
        encoder.encode_keepalive = lambda: ": keepalive\n\n"  # type: ignore[attr-defined]
    return encoder


def _get_auth_backend() -> Any:
    auth_backend_cls = get_backend_class("AUTH_BACKEND")
    if auth_backend_cls is None:
        return None
    return auth_backend_cls()


def authenticate_request(request: Any, *, auth_required: bool = False) -> AuthResult:
    """Authenticate and authorize request using configured backend."""
    require_auth = auth_required or bool(get_setting("REQUIRE_AUTHENTICATION", False))
    backend = _get_auth_backend()

    if backend is None:
        request.agui_user = None
        if require_auth:
            return AuthResult(
                allowed=False,
                status_code=500,
                message="Authentication backend is not configured",
            )
        return AuthResult(allowed=True)

    user = backend.authenticate(request)
    request.agui_user = user

    if require_auth and user is None:
        return AuthResult(
            allowed=False,
            status_code=401,
            message="Authentication required",
        )

    request_path = getattr(request, "path", "")
    if user is not None and not backend.check_permission(user, request_path):
        return AuthResult(
            allowed=False,
            status_code=403,
            message="Permission denied",
            user=user,
        )

    return AuthResult(allowed=True, user=user)


def _get_state_backend() -> Any | None:
    state_backend_cls = get_backend_class("STATE_BACKEND")
    if state_backend_cls is None:
        return None
    return state_backend_cls()


def get_error_message(exc: Exception, *, policy: str) -> str:
    """Build client-facing error message based on resolved policy."""
    if policy == "full":
        return str(exc)
    return "Agent execution failed"


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _to_async_iterator(value: Any) -> AsyncIterator[Any]:
    if hasattr(value, "__aiter__"):
        return value

    resolved = await _maybe_await(value)
    if hasattr(resolved, "__aiter__"):
        return resolved

    if isinstance(resolved, Iterable):

        async def _iter_sync() -> AsyncIterator[Any]:
            for item in resolved:
                yield item

        return _iter_sync()

    raise TypeError("Expected async iterator, awaitable async iterator, or iterable")


def _unwrap_bound_callable(func: Any) -> Any:
    """Return plain callable if class-level function is accessed as bound method."""
    if inspect.ismethod(func):
        return func.__func__
    return func


async def _translate_events(
    event: BaseEvent,
    translate_event: Any,
) -> AsyncIterator[BaseEvent]:
    if translate_event is None:
        yield event
        return

    translated = _unwrap_bound_callable(translate_event)(event)
    translated_iter = await _to_async_iterator(translated)
    async for item in translated_iter:
        yield item


async def prepare_input(
    input_data: RunAgentInput,
    request: Any,
    get_system_message: Any = None,
) -> tuple[RunAgentInput, Any]:
    """Prepare RunAgentInput with optional system message and persisted state."""
    prepared = input_data

    if get_system_message is not None:
        system_message = await _maybe_await(
            _unwrap_bound_callable(get_system_message)(request)
        )
        if system_message:
            system = SystemMessage(
                id=f"system-{prepared.run_id}",
                content=str(system_message),
            )
            prepared = prepared.model_copy(
                update={"messages": [system, *prepared.messages]}
            )

    state_backend = _get_state_backend()
    if state_backend is not None and prepared.state is None:
        loaded_state = await _maybe_await(state_backend.load_state(prepared.thread_id))
        if loaded_state is not None:
            prepared = prepared.model_copy(update={"state": loaded_state})

    return prepared, state_backend


class AGUIRunner:
    """Shared AG-UI runner for framework adapters."""

    def __init__(
        self,
        *,
        run_agent: Any,
        request: Any,
        encoder: StreamEncoder | None = None,
        translate_event: Any = None,
        get_system_message: Any = None,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
    ) -> None:
        self.run_agent = run_agent
        self.request = request
        self.encoder = encoder or build_event_encoder()
        self.translate_event = translate_event
        self.get_system_message = get_system_message
        self.config = AGUIExecutionConfig.from_settings(
            emit_run_lifecycle_events=emit_run_lifecycle_events,
            error_detail_policy=error_detail_policy,
            state_save_policy=state_save_policy,
        )
        self._last_state: Any = None
        self._saw_state_snapshot = False

    async def _iter_events(self, input_data: RunAgentInput) -> AsyncIterator[BaseEvent]:
        run_agent = _unwrap_bound_callable(self.run_agent)
        agent_result = run_agent(input_data, self.request)
        agent_iter = await _to_async_iterator(agent_result)
        async for event in agent_iter:
            async for translated in _translate_events(event, self.translate_event):
                if translated.type == EventType.STATE_SNAPSHOT and isinstance(
                    translated, StateSnapshotEvent
                ):
                    self._last_state = translated.snapshot
                    self._saw_state_snapshot = True
                yield translated

    async def _iter_events_with_keepalive(
        self,
        events: AsyncIterator[BaseEvent],
    ) -> AsyncIterator[BaseEvent | None]:
        keepalive = self.config.keepalive_interval
        timeout = self.config.timeout

        if keepalive <= 0 and timeout <= 0:
            async for event in events:
                yield event
            return

        loop = asyncio.get_running_loop()
        started = loop.time()
        next_event_task: asyncio.Task[BaseEvent] | None = None

        try:
            while True:
                if timeout > 0:
                    elapsed = loop.time() - started
                    if elapsed >= timeout:
                        raise TimeoutError("AG-UI stream timed out")

                wait_time: float | None = None
                if keepalive > 0:
                    wait_time = float(keepalive)
                if timeout > 0:
                    elapsed = loop.time() - started
                    remaining = max(timeout - elapsed, 0.0)
                    wait_time = (
                        remaining if wait_time is None else min(wait_time, remaining)
                    )

                if next_event_task is None:
                    next_event_task = asyncio.create_task(anext(events))

                if wait_time is None:
                    try:
                        yield await next_event_task
                    except StopAsyncIteration:
                        return
                    finally:
                        next_event_task = None
                    continue

                done, _ = await asyncio.wait({next_event_task}, timeout=wait_time)
                if not done:
                    elapsed = loop.time() - started
                    if timeout > 0 and elapsed >= timeout:
                        raise TimeoutError("AG-UI stream timed out")
                    yield None
                    continue

                try:
                    yield next_event_task.result()
                except StopAsyncIteration:
                    return
                finally:
                    next_event_task = None
        finally:
            if next_event_task is not None:
                next_event_task.cancel()
                with suppress(asyncio.CancelledError, StopAsyncIteration):
                    await next_event_task

    async def _persist_state(
        self,
        state_backend: Any | None,
        *,
        thread_id: str,
        run_id: str,
    ) -> None:
        if state_backend is None:
            return

        policy = self.config.state_save_policy
        if policy == "disabled":
            return
        if policy == "on_snapshot" and not self._saw_state_snapshot:
            return

        if self._last_state is None:
            if hasattr(state_backend, "delete_state"):
                await _maybe_await(state_backend.delete_state(thread_id))
            return

        await _maybe_await(
            state_backend.save_state(
                thread_id,
                run_id,
                self._last_state,
            )
        )

    def _build_error_event(self, exc: Exception) -> RunErrorEvent:
        return RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=get_error_message(exc, policy=self.config.error_detail_policy),
            code="timeout" if isinstance(exc, TimeoutError) else None,
        )

    async def stream(self, input_data: RunAgentInput) -> AsyncIterator[str]:
        """Yield encoded AG-UI packets."""
        prepared_input, state_backend = await prepare_input(
            input_data,
            self.request,
            self.get_system_message,
        )
        self._last_state = prepared_input.state

        try:
            if self.config.emit_run_lifecycle_events:
                yield self.encoder.encode(
                    RunStartedEvent(
                        type=EventType.RUN_STARTED,
                        thread_id=prepared_input.thread_id,
                        run_id=prepared_input.run_id,
                        parent_run_id=prepared_input.parent_run_id,
                    )
                )

            async for event in self._iter_events_with_keepalive(
                self._iter_events(prepared_input)
            ):
                if event is None:
                    yield self.encoder.encode_keepalive()
                    continue
                yield self.encoder.encode(event)

            if self.config.emit_run_lifecycle_events:
                yield self.encoder.encode(
                    RunFinishedEvent(
                        type=EventType.RUN_FINISHED,
                        thread_id=prepared_input.thread_id,
                        run_id=prepared_input.run_id,
                        result=self._last_state,
                    )
                )

            await self._persist_state(
                state_backend,
                thread_id=prepared_input.thread_id,
                run_id=prepared_input.run_id,
            )

        except Exception as exc:
            logger.exception("Error during agent execution")
            yield self.encoder.encode(self._build_error_event(exc))

    async def collect(self, input_data: RunAgentInput) -> AGUICollectedRun:
        """Collect AG-UI events for non-streaming responses."""
        prepared_input, state_backend = await prepare_input(
            input_data,
            self.request,
            self.get_system_message,
        )
        self._last_state = prepared_input.state

        events: list[BaseEvent] = []

        try:
            if self.config.emit_run_lifecycle_events:
                events.append(
                    RunStartedEvent(
                        type=EventType.RUN_STARTED,
                        thread_id=prepared_input.thread_id,
                        run_id=prepared_input.run_id,
                        parent_run_id=prepared_input.parent_run_id,
                    )
                )

            if self.config.timeout > 0:
                async with asyncio.timeout(self.config.timeout):
                    async for event in self._iter_events(prepared_input):
                        events.append(event)
            else:
                async for event in self._iter_events(prepared_input):
                    events.append(event)

            if self.config.emit_run_lifecycle_events:
                events.append(
                    RunFinishedEvent(
                        type=EventType.RUN_FINISHED,
                        thread_id=prepared_input.thread_id,
                        run_id=prepared_input.run_id,
                        result=self._last_state,
                    )
                )

            await self._persist_state(
                state_backend,
                thread_id=prepared_input.thread_id,
                run_id=prepared_input.run_id,
            )

            return AGUICollectedRun(
                thread_id=prepared_input.thread_id,
                run_id=prepared_input.run_id,
                events=events,
                has_error=False,
            )

        except Exception as exc:
            logger.exception("Error during agent execution")
            events.append(self._build_error_event(exc))
            return AGUICollectedRun(
                thread_id=prepared_input.thread_id,
                run_id=prepared_input.run_id,
                events=events,
                has_error=True,
            )
