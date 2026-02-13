"""Django app configuration for django-agui."""

from django.apps import AppConfig


class DjangoAguiConfig(AppConfig):
    """Configuration for the django-agui application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_agui"
    verbose_name = "Django AG-UI"

    def ready(self) -> None:
        """Register Django system checks."""
        import django_agui.checks  # noqa: F401
