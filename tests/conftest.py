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
