# django-agui

`django-agui` helps you run fully AG-UI-compatible agent servers using standard Django patterns.

## Why django-agui

- **AG-UI protocol compatibility** - Full support for the AG-UI streaming protocol
- **Multi-framework support** - Works with Django, DRF, Django Ninja, and Django Bolt
- **Django-native** - Uses Django views, URL routing, auth, and settings
- **Simple API** - Just provide your agent function, we'll handle the rest
- **Production-focused** - Async views, SSE keepalive/timeout, auth and CORS controls

## Installation

```bash
pip install django-agui
```

For specific framework support, install the corresponding package:

```bash
# Django REST Framework
pip install djangorestframework

# Django Ninja
pip install django-ninja

# Django Bolt
pip install django-bolt
```

## Quick Start

### 1. Create your agent function

```python
# agents.py
from ag_ui.core import (
    EventType,
    TextMessageContentEvent,
    TextMessageStartEvent,
    TextMessageEndEvent,
)

async def echo_agent(input_data, request):
    """Simple echo agent."""
    user_message = input_data.messages[-1].content[0].text

    yield TextMessageStartEvent(
        type=EventType.TEXT_MESSAGE_START,
        message_id="msg-1",
    )

    yield TextMessageContentEvent(
        type=EventType.TEXT_MESSAGE_CONTENT,
        message_id="msg-1",
        delta=f"Echo: {user_message}",
    )

    yield TextMessageEndEvent(
        type=EventType.TEXT_MESSAGE_END,
        message_id="msg-1",
    )
```

### 2. Wire up URL patterns

#### Option 1: Pure Django (Default)

```python
# urls.py
from django.urls import path
from django_agui import get_agui_urlpatterns
from .agents import echo_agent

urlpatterns = [
    *get_agui_urlpatterns(path_prefix="agent/", run_agent=echo_agent),
]
```

#### Option 2: Django REST Framework

```python
# urls.py
from django_agui.contrib.drf import get_drf_urlpatterns
from .agents import echo_agent

urlpatterns = [
    *get_drf_urlpatterns(path_prefix="agent/", run_agent=echo_agent),
]
```

#### Option 3: Django Ninja

```python
# urls.py
from django_agui.contrib.ninja import get_ninja_urlpatterns
from .agents import echo_agent

urlpatterns = [
    *get_ninja_urlpatterns(path_prefix="agent/", run_agent=echo_agent),
]
```

#### Option 4: Django Bolt

```python
# urls.py
from django_agui.contrib.bolt import get_bolt_urlpatterns
from .agents import echo_agent

urlpatterns = [
    *get_bolt_urlpatterns(path_prefix="agent/", run_agent=echo_agent),
]
```

### 3. Run

```bash
python manage.py runserver
```

## Advanced Usage

### Multi-agent Router (Pure Django)

```python
# urls.py
from django_agui import AGUIRouter

router = AGUIRouter()

router.register("echo", echo_agent)
router.register("research", research_agent)
router.register("coder", coder_agent)

urlpatterns = router.urls
```

### Decorator-based (Pure Django)

```python
# views.py
from django_agui.decorators import agui_view
from django.urls import path

@agui_view(auth_required=True)
async def my_agent(input_data, request):
    yield TextMessageContentEvent(...)

urlpatterns = [
    path('agent/', my_agent),
]
```

### Backend Classes

For more control, use the backend classes directly:

```python
from django_agui.contrib.drf import DRFBackend
from django_agui.contrib.ninja import NinjaBackend
from django_agui.contrib.bolt import BoltBackend

# DRF
drf_backend = DRFBackend()
view = drf_backend.create_view(run_agent=my_agent, streaming=True)

# Ninja
ninja_backend = NinjaBackend()
api = ninja_backend.create_api(run_agent=my_agent)

# Bolt
bolt_backend = BoltBackend()
api = bolt_backend.create_api(run_agent=my_agent)
```

## Configuration

Add AG-UI settings to your Django settings:

```python
# settings.py
AGUI = {
    # Authentication
    "AUTH_BACKEND": "django_agui.backends.auth.DjangoAuthBackend",
    "REQUIRE_AUTHENTICATION": False,
    "ALLOWED_ORIGINS": ["https://app.example.com"],

    # SSE settings
    "SSE_KEEPALIVE_INTERVAL": 30,
    "SSE_TIMEOUT": 300,

    # Runtime behavior
    "EMIT_RUN_LIFECYCLE_EVENTS": True,
    "ERROR_DETAIL_POLICY": "safe",  # or "full"

    # Request limits
    "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
}
```

## Database Storage (Optional)

django-agui provides an optional Django ORM storage backend for persisting conversations, messages, and tool calls. **By default, this is disabled and no database migrations are required.**

### Quick Start (No DB Storage)

Use django-agui without any database storage (default):

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_agui",
]

# No AGUI setting needed - DB storage is disabled by default
```

That's it! No migrations needed.

### Enable Database Storage

To persist conversations in the database:

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_agui",
]

DATABASE_ROUTERS = [
    "django_agui.storage.router.AGUIDBRouter",
]

AGUI = {
    "USE_DB_STORAGE": True,  # Enable DB storage
}
```

Then run migrations:

```bash
python manage.py migrate
```

### Why Use Database Storage?

The DB storage backend provides:

- **Conversation history**: Persist threads, runs, and messages
- **Tool call tracking**: Store tool arguments and results
- **Event logging**: Optional event storage for debugging
- **File attachments**: Store images, documents, etc.

### Storage Backend Usage

```python
from django_agui.storage import DjangoStorageBackend

# Initialize storage
storage = DjangoStorageBackend()
await storage.initialize()

# Save a conversation thread
from django_agui.storage import Thread
thread = Thread(
    id="thread-123",
    user_id="user-456",
    metadata={"topic": "support"}
)
await storage.threads.save_thread(thread)

# Save messages
from django_agui.storage import Message
message = Message(
    id="msg-001",
    thread_id="thread-123",
    role="user",
    content="Hello!",
    content_type="text"
)
await storage.messages.save_message(message)

# Retrieve conversation history
messages = await storage.messages.list_messages(thread_id="thread-123")
```

### Disable Migrations

If you previously enabled DB storage and want to disable it:

```python
# settings.py
AGUI = {
    "USE_DB_STORAGE": False,  # Disable DB storage
}
```

The router will automatically skip all AG-UI migrations.

## Project Structure

```
django-agui/
├── src/django_agui/
│   ├── __init__.py              # Core exports only
│   ├── settings.py              # Django-style settings
│   ├── urls.py                  # Core Django URL routing
│   ├── views.py                 # Core Django views
│   ├── decorators.py            # @agui_view decorator
│   ├── encoders.py              # SSE event encoding
│   ├── types.py                 # Type definitions
│   ├── backends/
│   │   └── auth.py              # Django auth backend
│   └── contrib/                 # Framework integrations
│       ├── drf/                 # Django REST Framework
│       ├── ninja/               # Django Ninja
│       └── bolt/                # Django Bolt
```

## API Reference

### Core Django

```python
from django_agui import (
    AGUIRouter,
    get_agui_urlpatterns,
    agui_view,
)
```

### Django REST Framework

```python
from django_agui.contrib.drf import (
    DRFBackend,
    AGUIView,
    AGUIRestView,
    get_drf_urlpatterns,
    create_drf_view,
)
```

### Django Ninja

```python
from django_agui.contrib.ninja import (
    NinjaBackend,
    get_ninja_urlpatterns,
    create_ninja_api,
)
```

### Django Bolt

```python
from django_agui.contrib.bolt import (
    BoltBackend,
    get_bolt_urlpatterns,
    create_bolt_api,
)
```

## Testing

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests (requires frameworks)
pytest tests/integration/

# Run with coverage
pytest --cov=django_agui
```

## Production Deployment

### Nginx Configuration

```nginx
location /agent/ {
    proxy_pass http://localhost:8000;
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

## License

MIT. See LICENSE.
