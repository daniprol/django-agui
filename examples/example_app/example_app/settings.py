"""Example Django app for framework integrations."""

import os
from pathlib import Path

import django
from django.core.management import execute_from_command_line

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "django_vite",
    "django_agui",
    "example_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "example_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "example_app.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "dev_server_port": 5173,
        "dev_server_host": "localhost",
        "static_url_prefix": "static/",
    }
}

AGUI = {
    "USE_DB_STORAGE": os.getenv("AGUI_USE_DB_STORAGE", "false").lower() == "true",
}

AGUI_AGENTS = {
    "langgraph-assistant": {
        "framework": "langgraph",
        "llm_provider": os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        "model": os.getenv("DEFAULT_MODEL", "gpt-4o"),
        "description": "LangGraph assistant agent",
        "system_prompt": "You are a helpful AI assistant.",
    },
    "llamaindex-assistant": {
        "framework": "llamaindex",
        "llm_provider": os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        "model": os.getenv("DEFAULT_MODEL", "gpt-4o"),
        "description": "LlamaIndex assistant agent",
        "system_prompt": "You are a helpful AI assistant.",
    },
    "agno-assistant": {
        "framework": "agno",
        "llm_provider": os.getenv("DEFAULT_LLM_PROVIDER", "openai"),
        "model": os.getenv("DEFAULT_MODEL", "gpt-4o"),
        "description": "Agno assistant agent",
    },
}

django.setup()


if __name__ == "__main__":
    execute_from_command_line()
