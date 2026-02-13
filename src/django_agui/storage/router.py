"""Database router for optional AG-UI ORM tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import Model


class AGUIDBRouter:
    """Conditionally enable migrations for ``django_agui`` models.

    When ``AGUI['USE_DB_STORAGE']`` is ``False`` (default), migrations for
    the ``django_agui`` app are skipped.
    """

    app_label = "django_agui"

    def _use_db_storage(self) -> bool:
        from django.conf import settings

        agui_settings = getattr(settings, "AGUI", {})
        return bool(agui_settings.get("USE_DB_STORAGE", False))

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: dict,
    ) -> bool | None:
        """Allow AG-UI migrations only when DB storage is enabled."""
        if app_label != self.app_label:
            return None
        return None if self._use_db_storage() else False

    def db_for_read(self, model: type[Model], **hints: dict) -> str | None:
        """Route AG-UI model reads to the default database."""
        return "default" if model._meta.app_label == self.app_label else None

    def db_for_write(self, model: type[Model], **hints: dict) -> str | None:
        """Route AG-UI model writes to the default database."""
        return "default" if model._meta.app_label == self.app_label else None

    def allow_relation(self, obj1: Model, obj2: Model, **hints: dict) -> bool | None:
        """Allow relations involving AG-UI models."""
        is_agui_relation = (
            obj1._meta.app_label == self.app_label
            or obj2._meta.app_label == self.app_label
        )
        return True if is_agui_relation else None
