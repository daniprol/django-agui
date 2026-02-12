"""Pytest configuration for django-agui tests."""

import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")


import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "django_agui",
        ],
        USE_TZ=True,
        AGUI={},
    )

django.setup()


# Fixtures for testing
import pytest
from ag_ui.core import EventType, TextMessageContentEvent, TextMessageStartEvent


@pytest.fixture
def mock_agent():
    """Fixture providing a mock agent function."""

    async def agent(input_data, request):
        yield TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id="msg-1",
        )
        yield TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id="msg-1",
            delta="Hello from mock agent",
        )

    return agent


@pytest.fixture
def mock_request():
    """Fixture providing a mock request object."""

    class MockRequest:
        def __init__(self):
            self.user = MockUser()

    class MockUser:
        def __init__(self):
            self.is_authenticated = False
            self.username = "anonymous"

    return MockRequest()


@pytest.fixture
def mock_run_input():
    """Fixture providing a mock RunAgentInput."""
    from ag_ui.core import RunAgentInput

    return RunAgentInput(
        thread_id="test-thread",
        run_id="test-run",
        messages=[],
        tools=[],
        context=[],
    )
