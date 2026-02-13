"""Shared runtime utilities for AG-UI request handling and streaming."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
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


def is_json_content_type(content_type: str | None) -> bool:
    """Return True when request Content-Type is JSON (charset allowed)."""
    if not content_type:
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json"


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
    meta_key = f"HTTP_{key.upper().replace('-', '_')}"
    meta = getattr(request, "META", {})
    return (
        meta.get(meta_key)
        or meta.get(key.upper().replace("-", "_"))
        or meta.get(f"HTTP_{meta_key}")
    )


def get_request_origin(request: Any) -> str | None:
    """Get Origin header from a request."""
    return get_request_header(request, "Origin")


def resolve_allowed_origins(allowed_origins: list[str] | None) -> list[str] | None:
    """Resolve allowed origins from view overrides or global settings."""
    if allowed_origins is not None:
        return allowed_origins
    global_origins = get_setting("ALLOWED_ORIGINS")
    if global_origins is None:
        return None
    if isinstance(global_origins, (list, tuple)):
        return [str(origin) for origin in global_origins]
    return [str(global_origins)]


def is_origin_allowed(origin: str | None, allowed_origins: list[str] | None) -> bool:
    """Check whether request origin is allowed."""
    if allowed_origins is None:
        return True
    if origin is None:
        return True
    if "*" in allowed_origins:
        return True
    return origin in allowed_origins


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


def build_event_encoder() -> StreamEncoder:
    """Build event encoder from settings."""
    encoder_cls = get_backend_class("EVENT_ENCODER")
    if encoder_cls is None:
        return SSEEventEncoder()
    encoder = encoder_cls()
    if not hasattr(encoder, "encode"):
        raise TypeError("EVENT_ENCODER must implement an encode(event) method")
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


def get_error_message(exc: Exception, *, policy: str | None = None) -> str:
    """Build client-facing error message based on configured policy."""
    resolved_policy = policy or str(get_setting("ERROR_DETAIL_POLICY", "safe"))
    if resolved_policy == "full":
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
    ) -> None:
        self.run_agent = run_agent
        self.request = request
        self.encoder = encoder or build_event_encoder()
        self.translate_event = translate_event
        self.get_system_message = get_system_message
        self.emit_run_lifecycle_events = (
            bool(get_setting("EMIT_RUN_LIFECYCLE_EVENTS", True))
            if emit_run_lifecycle_events is None
            else emit_run_lifecycle_events
        )
        self.error_detail_policy = (
            str(get_setting("ERROR_DETAIL_POLICY", "safe"))
            if error_detail_policy is None
            else error_detail_policy
        )
        self.keepalive_interval = get_setting("SSE_KEEPALIVE_INTERVAL", 30)
        self.timeout = get_setting("SSE_TIMEOUT", 300)
        self._last_state: Any = None

    async def _iter_events(self, input_data: RunAgentInput) -> AsyncIterator[BaseEvent]:
        run_agent = _unwrap_bound_callable(self.run_agent)
        agent_result = run_agent(input_data, self.request)
        agent_iter = await _to_async_iterator(agent_result)
        async for event in agent_iter:
            async for translated in _translate_events(event, self.translate_event):
                if translated.type == EventType.STATE_SNAPSHOT:
                    snapshot = translated
                    if isinstance(snapshot, StateSnapshotEvent):
                        self._last_state = snapshot.snapshot
                yield translated

    async def _iter_events_with_keepalive(
        self,
        events: AsyncIterator[BaseEvent],
    ) -> AsyncIterator[BaseEvent | None]:
        keepalive = int(self.keepalive_interval) if self.keepalive_interval else 0
        timeout = int(self.timeout) if self.timeout else 0

        if keepalive <= 0 and timeout <= 0:
            async for event in events:
                yield event
            return

        started = asyncio.get_running_loop().time()
        while True:
            if timeout > 0:
                elapsed = asyncio.get_running_loop().time() - started
                if elapsed >= timeout:
                    raise TimeoutError("AG-UI stream timed out")

            wait_time: float | None = None
            if keepalive > 0:
                wait_time = float(keepalive)
            if timeout > 0:
                elapsed = asyncio.get_running_loop().time() - started
                remaining = max(timeout - elapsed, 0.0)
                wait_time = remaining if wait_time is None else min(wait_time, remaining)

            try:
                if wait_time is None:
                    event = await anext(events)
                else:
                    event = await asyncio.wait_for(anext(events), timeout=wait_time)
                yield event
            except StopAsyncIteration:
                return
            except TimeoutError:
                elapsed = asyncio.get_running_loop().time() - started
                if timeout > 0 and elapsed >= timeout:
                    raise
                yield None

    async def stream(self, input_data: RunAgentInput) -> AsyncIterator[str]:
        """Yield encoded AG-UI packets."""
        prepared_input, state_backend = await prepare_input(
            input_data,
            self.request,
            self.get_system_message,
        )
        self._last_state = prepared_input.state

        try:
            if self.emit_run_lifecycle_events:
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

            if self.emit_run_lifecycle_events:
                yield self.encoder.encode(
                    RunFinishedEvent(
                        type=EventType.RUN_FINISHED,
                        thread_id=prepared_input.thread_id,
                        run_id=prepared_input.run_id,
                        result=self._last_state,
                    )
                )

            if state_backend is not None and self._last_state is not None:
                await _maybe_await(
                    state_backend.save_state(
                        prepared_input.thread_id,
                        prepared_input.run_id,
                        self._last_state,
                    )
                )

        except Exception as exc:
            logger.exception("Error during agent execution")
            code = "timeout" if isinstance(exc, TimeoutError) else None
            yield self.encoder.encode(
                RunErrorEvent(
                    type=EventType.RUN_ERROR,
                    message=get_error_message(exc, policy=self.error_detail_policy),
                    code=code,
                )
            )
