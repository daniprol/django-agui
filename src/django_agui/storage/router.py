"""Database router for optional AG-UI storage.

This router allows django-agui to work without database migrations
when the DB storage backend is not being used.

Usage:
    Add to your settings.py:

    DATABASE_ROUTERS = ['django_agui.storage.router.AGUIDBRouter']

    AGUI = {
        'USE_DB_STORAGE': True,  # Set to True to enable DB storage
    }

    Then run migrations if needed:
    python manage.py migrate
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import Model


class AGUIDBRouter:
    """Database router for optional AG-UI storage.

        This router controls whether AG-UI migrations are applied based on
    the USE_DB_STORAGE setting. When disabled (default), migrations are
    skipped and no database tables are created.

        Example:
            # settings.py - AG-UI without DB storage (default, no migrations)
            DATABASE_ROUTERS = ['django_agui.storage.router.AGUIDBRouter']

            AGUI = {
                'USE_DB_STORAGE': False,  # Default: no migrations
            }

            # settings.py - AG-UI with DB storage (requires migrations)
            DATABASE_ROUTERS = ['django_agui.storage.router.AGUIDBRouter']

            AGUI = {
                'USE_DB_STORAGE': True,  # Enable: run migrations
            }
    """

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: dict,
    ) -> bool | None:
        """Determine if migrations should run for AG-UI models.

        Args:
            db: Database alias
            app_label: Application label
            model_name: Name of the model being migrated
            **hints: Additional hints from the migration

        Returns:
            False if app is django_agui and USE_DB_STORAGE is False
            None otherwise (let Django decide)
        """
        if app_label != "django_agui":
            return None  # Not our app, let Django handle it

        # Check if DB storage is enabled
        from django.conf import settings

        agui_settings = getattr(settings, "AGUI", {})
        use_db_storage = agui_settings.get("USE_DB_STORAGE", False)

        if use_db_storage:
            return None  # Allow migrations to run

        return False  # Skip all migrations for django_agui

    def db_for_read(self, model: type[Model], **hints: dict) -> str | None:
        """Route read operations to default database."""
        if model._meta.app_label == "django_agui":
            return "default"
        return None

    def db_for_write(self, model: type[Model], **hints: dict) -> str | None:
        """Route write operations to default database."""
        if model._meta.app_label == "django_agui":
            return "default"
        return None

    def allow_relation(self, obj1: Model, obj2: Model, **hints: dict) -> bool | None:
        """Allow relations between AG-UI models and other models."""
        if (
            obj1._meta.app_label == "django_agui"
            or obj2._meta.app_label == "django_agui"
        ):
            return True
        return None
