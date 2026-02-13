"""Unit tests for framework adapters using local stubs (no optional deps needed)."""

from __future__ import annotations

import importlib
import sys
import types

from ag_ui.core import EventType, RunAgentInput, TextMessageContentEvent
import pytest


def _purge_modules(*prefixes: str) -> None:
    for name in list(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(name, None)


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


class _FakeRequest:
    def __init__(
        self,
        *,
        origin: str | None = None,
        body: bytes | None = None,
        content_type: str = "application/json",
        path: str = "/agent/",
        method: str = "POST",
    ) -> None:
        self.path = path
        self.method = method
        self.content_type = content_type
        self.body = body or b""
        self.headers: dict[str, str] = {}
        self.META: dict[str, str] = {}
        if origin is not None:
            self.headers["Origin"] = origin
            self.META["HTTP_ORIGIN"] = origin


async def _collect_streaming_chunks(response) -> str:
    chunks: list[str] = []
    stream = response.streaming_content
    if hasattr(stream, "__aiter__"):
        async for chunk in stream:
            chunks.append(
                chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
            )
    else:
        for chunk in stream:
            chunks.append(
                chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
            )
    return "".join(chunks)


def _install_fake_rest_framework(monkeypatch: pytest.MonkeyPatch) -> None:
    _purge_modules(
        "rest_framework",
        "django_agui.contrib.drf.backend",
        "django_agui.contrib.drf.views",
    )

    rest_framework = types.ModuleType("rest_framework")
    rest_framework.__path__ = []  # type: ignore[attr-defined]

    status_mod = types.ModuleType("rest_framework.status")
    status_mod.HTTP_200_OK = 200
    status_mod.HTTP_204_NO_CONTENT = 204
    status_mod.HTTP_400_BAD_REQUEST = 400
    status_mod.HTTP_500_INTERNAL_SERVER_ERROR = 500

    request_mod = types.ModuleType("rest_framework.request")
    request_mod.Request = _FakeRequest

    response_mod = types.ModuleType("rest_framework.response")

    class _Response(dict):
        def __init__(self, data=None, status=200):
            super().__init__()
            self.data = data
            self.status_code = status

    response_mod.Response = _Response

    views_mod = types.ModuleType("rest_framework.views")

    class _APIView:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        @classmethod
        def as_view(cls, **initkwargs):
            async def _view(request, *args, **kwargs):
                self = cls(**initkwargs)
                handler = getattr(self, request.method.lower())
                result = handler(request, *args, **kwargs)
                if hasattr(result, "__await__"):
                    return await result
                return result

            return _view

    views_mod.APIView = _APIView

    rest_framework.status = status_mod  # type: ignore[attr-defined]
    rest_framework.request = request_mod  # type: ignore[attr-defined]
    rest_framework.response = response_mod  # type: ignore[attr-defined]
    rest_framework.views = views_mod  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "rest_framework", rest_framework)
    monkeypatch.setitem(sys.modules, "rest_framework.status", status_mod)
    monkeypatch.setitem(sys.modules, "rest_framework.request", request_mod)
    monkeypatch.setitem(sys.modules, "rest_framework.response", response_mod)
    monkeypatch.setitem(sys.modules, "rest_framework.views", views_mod)


def _install_fake_ninja(monkeypatch: pytest.MonkeyPatch) -> type[Exception]:
    _purge_modules(
        "ninja",
        "django_agui.contrib.ninja.backend",
        "django_agui.contrib.ninja.views",
    )

    ninja = types.ModuleType("ninja")
    ninja.__path__ = []  # type: ignore[attr-defined]

    class _NinjaAPI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.routes: list[tuple[str, str, object]] = []
            self.urls = ("fake-ninja-urlconf", "fake-ninja-app", "fake-ninja-namespace")

        def post(self, path):
            def _decorator(func):
                self.routes.append(("POST", path, func))
                return func

            return _decorator

    ninja.NinjaAPI = _NinjaAPI  # type: ignore[attr-defined]

    errors_mod = types.ModuleType("ninja.errors")

    class _HttpError(Exception):
        def __init__(self, status_code: int, message: str):
            super().__init__(message)
            self.status_code = status_code
            self.message = message

    errors_mod.HttpError = _HttpError
    ninja.errors = errors_mod  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "ninja", ninja)
    monkeypatch.setitem(sys.modules, "ninja.errors", errors_mod)
    return _HttpError


def _install_fake_bolt(monkeypatch: pytest.MonkeyPatch) -> type[Exception]:
    _purge_modules(
        "django_bolt",
        "django_agui.contrib.bolt.backend",
        "django_agui.contrib.bolt.views",
    )

    django_bolt = types.ModuleType("django_bolt")
    django_bolt.__path__ = []  # type: ignore[attr-defined]

    class _BoltAPI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.routes: list[tuple[str, str, object]] = []
            self.urls = ("fake-bolt-urlconf", "fake-bolt-app", "fake-bolt-namespace")

        def post(self, path):
            def _decorator(func):
                self.routes.append(("POST", path, func))
                return func

            return _decorator

    django_bolt.BoltAPI = _BoltAPI  # type: ignore[attr-defined]

    exceptions_mod = types.ModuleType("django_bolt.exceptions")

    class _HttpError(Exception):
        def __init__(self, status_code: int, message: str):
            super().__init__(message)
            self.status_code = status_code
            self.message = message

    exceptions_mod.HttpException = _HttpError
    django_bolt.exceptions = exceptions_mod  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "django_bolt", django_bolt)
    monkeypatch.setitem(sys.modules, "django_bolt.exceptions", exceptions_mod)
    return _HttpError


@pytest.mark.asyncio
async def test_drf_backend_and_views_with_stubs(settings, monkeypatch):
    """DRF adapter path works end-to-end with local rest_framework stubs."""
    settings.AGUI = {}
    _install_fake_rest_framework(monkeypatch)

    drf_backend = importlib.import_module("django_agui.contrib.drf.backend")

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="hello-from-drf",
        )

    payload = _run_input().model_dump_json(by_alias=True).encode("utf-8")

    stream_view_class = drf_backend.DRFBackend().create_view(
        run_agent=agent,
        allowed_origins=["https://app.test"],
        streaming=True,
    )
    stream_view = stream_view_class()
    stream_request = _FakeRequest(origin="https://app.test", body=payload)
    stream_response = await stream_view.post(stream_request)
    stream_payload = await _collect_streaming_chunks(stream_response)

    assert stream_response.status_code == 200
    assert stream_response["Access-Control-Allow-Origin"] == "https://app.test"
    assert '"type":"TEXT_MESSAGE_CONTENT"' in stream_payload

    rest_view_class = drf_backend.DRFBackend().create_view(
        run_agent=agent,
        allowed_origins=["https://app.test"],
        streaming=False,
    )
    rest_view = rest_view_class()
    rest_request = _FakeRequest(origin="https://app.test", body=payload)
    rest_response = await rest_view.post(rest_request)

    assert rest_response.status_code == 200
    assert rest_response["Access-Control-Allow-Origin"] == "https://app.test"
    assert any(
        event["type"] == "TEXT_MESSAGE_CONTENT"
        for event in rest_response.data["events"]
    )


@pytest.mark.asyncio
async def test_ninja_backend_and_endpoint_with_stubs(settings, monkeypatch):
    """Ninja adapter path works end-to-end with local ninja stubs."""
    settings.AGUI = {}
    http_error = _install_fake_ninja(monkeypatch)

    ninja_backend = importlib.import_module("django_agui.contrib.ninja.backend")
    ninja_views = importlib.import_module("django_agui.contrib.ninja.views")

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="hello-from-ninja",
        )

    endpoint = ninja_views.create_ninja_endpoint(
        run_agent=agent,
        allowed_origins=["https://app.test"],
    )

    response = await endpoint(
        _FakeRequest(origin="https://app.test"),
        _run_input().model_dump(mode="json"),
    )
    payload = await _collect_streaming_chunks(response)

    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "https://app.test"
    assert '"type":"TEXT_MESSAGE_CONTENT"' in payload

    with pytest.raises(http_error) as exc:
        await endpoint(
            _FakeRequest(origin="https://blocked.test"),
            _run_input().model_dump(mode="json"),
        )
    assert exc.value.status_code == 403

    backend = ninja_backend.NinjaBackend()
    api = backend.create_api(run_agent=agent, title="AGUI")
    patterns = backend.get_urlpatterns("agent/", run_agent=agent)

    assert len(api.routes) == 1
    assert api.routes[0][1] == "/"
    assert len(patterns) == 1
    assert str(patterns[0].pattern) == "agent/"


@pytest.mark.asyncio
async def test_bolt_backend_and_endpoint_with_stubs(settings, monkeypatch):
    """Bolt adapter path works end-to-end with local django_bolt stubs."""
    settings.AGUI = {}
    http_exception = _install_fake_bolt(monkeypatch)

    bolt_backend = importlib.import_module("django_agui.contrib.bolt.backend")
    bolt_views = importlib.import_module("django_agui.contrib.bolt.views")

    async def agent(input_data, request):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="hello-from-bolt",
        )

    endpoint = bolt_views.create_bolt_endpoint(
        run_agent=agent,
        allowed_origins=["https://app.test"],
    )

    response = await endpoint(
        _FakeRequest(origin="https://app.test"),
        _run_input().model_dump(mode="json"),
    )
    payload = await _collect_streaming_chunks(response)

    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "https://app.test"
    assert '"type":"TEXT_MESSAGE_CONTENT"' in payload

    with pytest.raises(http_exception) as exc:
        await endpoint(
            _FakeRequest(origin="https://blocked.test"),
            _run_input().model_dump(mode="json"),
        )
    assert exc.value.status_code == 403

    backend = bolt_backend.BoltBackend()
    api = backend.create_api(run_agent=agent, title="AGUI")
    patterns = backend.get_urlpatterns("agent/", run_agent=agent)

    assert len(api.routes) == 1
    assert api.routes[0][1] == "/"
    assert len(patterns) == 1
    assert str(patterns[0].pattern) == "agent/"
