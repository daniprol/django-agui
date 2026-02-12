# django-agui

`django-agui` helps you run fully AG-UI-compatible agent servers using standard Django patterns.

## Why django-agui

- **AG-UI protocol compatibility** - Full support for the AG-UI streaming protocol
- **Django-native** - Uses Django views, URL routing, auth, and settings
- **Simple API** - Just provide your agent function, we'll handle the rest
- **DRF support** - Optional Django REST Framework integration
- **Production-ready** - Async views, SSE streaming, proper error handling

## Quick Start

### Installation

```bash
pip install django-agui
```

For Django REST Framework support:
```bash
pip install django-agui[drf]
```

### Basic Usage

#### 1. Create your agent function

```python
# agents.py
from ag_ui.core import (
    EventType,
    TextMessageContentEvent,
    TextMessageStartEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
)

async def echo_agent(input_data, request):
    """Simple echo agent."""
    # Get user message
    user_message = input_data.messages[-1].content[0].text

    # Start text message
    yield TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id="msg-1",
    )

    # Stream content
    yield TextMessageContentEvent(
        type=EventType.TEXT_MESSAGE_CONTENT,
        message_id="msg-1",
        delta=f"Echo: {user_message}",
    )

    # End message
    yield TextMessageEndEvent(
        type=EventType.TEXT_MESSAGE_END,
        message_id="msg-1",
    )
```

#### 2. Wire up URL patterns

```python
# urls.py
from django.urls import path
from django_agui import get_agui_urlpatterns
from .agents import echo_agent

urlpatterns = [
    *get_agui_urlpatterns(
        path_prefix="agent/",
        run_agent=echo_agent,
    ),
]
```

That's it! Your agent is now accessible at `/agent/` and fully AG-UI compatible.

## API Reference

### `get_agui_urlpatterns()`

The simplest way to expose a single agent.

```python
get_agui_urlpatterns(
    path_prefix="agent/",           # URL path
    run_agent=my_agent_function,     # Your async agent function
    translate_event=None,            # Optional: translate custom events
    get_system_message=None,         # Optional: get system message
    auth_required=False,             # Optional: require authentication
    allowed_origins=None,            # Optional: CORS origins
)
```

### `AGUIRouter` / `MultiAgentRouter`

For multiple agents on the same server:

```python
from django_agui import AGUIRouter

router = AGUIRouter()

# Register multiple agents
router.register("echo", echo_agent)
router.register("research", research_agent)
router.register("code", code_agent)

urlpatterns = router.urls
```

### `@agui_view` Decorator

Decorate your agent function directly:

```python
from django_agui.decorators import agui_view
from django.urls import path

@agui_view(auth_required=True)
async def my_agent(input_data, request):
    yield TextMessageContentEvent(...)

urlpatterns = [
    path('agent/', my_agent),
]
```

### Custom View Class

For more control, create your own view:

```python
from django_agui.views import create_agui_view

MyAgentView = create_agui_view(
    run_agent=my_agent_function,
    translate_event=my_translator,
    auth_required=True,
)

urlpatterns = [
    path('agent/', MyAgentView.as_view()),
]
```

## Django REST Framework Support

For DRF integration, use the DRF-specific components:

```python
# urls.py
from django_agui.router_drf import AGUIRouter as AGUIDRFRouter
from .agents import my_agent

router = AGUIDRFRouter()
router.register("agent", my_agent, basename="my-agent")

urlpatterns = [
    path('api/', include(router.urls)),
]
```

Or use the REST view for non-streaming responses:

```python
from django_agui.views_drf import create_agui_rest_drf_view

MyAgentRestView = create_agui_rest_drf_view(my_agent)

urlpatterns = [
    path('api/agent/', MyAgentRestView.as_view()),
]
```

## Configuration

Add AG-UI settings to your Django settings:

```python
# settings.py
AGUI = {
    # Authentication
    "AUTH_BACKEND": "django_agui.backends.auth.DjangoAuthBackend",
    "REQUIRE_AUTHENTICATION": False,

    # State management (optional)
    "STATE_BACKEND": None,

    # SSE settings
    "SSE_KEEPALIVE_INTERVAL": 30,  # seconds
    "SSE_TIMEOUT": 300,             # seconds

    # Request limits
    "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,  # 10MB
}
```

## Advanced Usage

### Event Translation

If your agent produces custom events, translate them to AG-UI:

```python
async def my_custom_translator(event):
    """Translate MyFramework events to AG-UI events."""
    if isinstance(event, MyTextDelta):
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id=event.id,
            delta=event.text,
        )
    elif isinstance(event, MyToolCall):
        yield ToolCallStartEvent(
            type=EventType.TOOL_CALL_START,
            tool_call_id=event.id,
            tool_name=event.name,
        )

# Use it
get_agui_urlpatterns(
    path_prefix="agent/",
    run_agent=my_agent,
    translate_event=my_custom_translator,
)
```

### Authentication

Control access to your agents:

```python
# In your view or using the router
get_agui_urlpatterns(
    path_prefix="agent/",
    run_agent=my_agent,
    auth_required=True,
)
```

With DRF:

```python
from rest_framework.permissions import IsAuthenticated

class MyProtectedAgentView(AGUIView):
    permission_classes = [IsAuthenticated]
```

### Accessing Django Request

Your agent function receives the Django request:

```python
async def my_agent(input_data, request):
    # Access authenticated user
    user = request.user

    # Access headers
    api_key = request.headers.get("X-API-Key")

    # Yield events...
```

## Production Deployment

### Nginx Configuration

Critical for SSE streaming:

```nginx
location /agent/ {
    proxy_pass http://localhost:8000;

    # Required for SSE
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection "";
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
}
```

### Gunicorn

```bash
gunicorn myproject.asgi:application -w 4 -k uvicorn.workers.UvicornWorker
```

### ASGI Server

```bash
uvicorn myproject.asgi:application --workers 4
```

## Example: Complete Agent

```python
# agents.py
from ag_ui.core import (
    EventType,
    TextMessageContentEvent,
    TextMessageStartEvent,
    TextMessageEndEvent,
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
)

async def chat_agent(input_data, request):
    """Chat agent with tool support."""
    user_message = input_data.messages[-1].content[0].text

    # Start run
    yield TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id="msg-1",
    )

    # Stream response
    response = f"You said: {user_message}"
    for word in response.split():
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta=f"{word} ",
        )

    # End message
    yield TextMessageEndEvent(
        type=EventType.TEXT_MESSAGE_END,
        message_id="msg-1",
    )

# urls.py
from django.urls import path
from django_agui import get_agui_urlpatterns
from .agents import chat_agent

urlpatterns = [
    *get_agui_urlpatterns(
        path_prefix="chat/",
        run_agent=chat_agent,
    ),
]
```

## License

MIT. See LICENSE.
