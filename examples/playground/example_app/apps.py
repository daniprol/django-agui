"""Example app configuration."""

from django.apps import AppConfig


class ExampleAppConfig(AppConfig):
    """Example app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "example_app"
    verbose_name = "Example App"

    def ready(self):
        from django_agui.agents import load_agents_from_settings

        load_agents_from_settings()
