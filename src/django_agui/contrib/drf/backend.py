"""Django REST Framework backend for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django_agui.contrib.drf.views import AGUIRestView, AGUIView
from django_agui.urls import build_route_name, normalize_path_prefix


class DRFBackend:
    """Backend helper for wiring AG-UI endpoints into DRF."""

    streaming_view_class = AGUIView
    rest_view_class = AGUIRestView
    route_name_prefix = "agui-drf"

    def get_view_class(self, *, streaming: bool) -> type:
        """Return the DRF view class for the requested response mode."""
        return self.streaming_view_class if streaming else self.rest_view_class

    def create_view(
        self,
        run_agent: Callable[..., Any],
        translate_event: Callable[[Any], Any] | None = None,
        get_system_message: Callable[[Any], str | None] | None = None,
        auth_required: bool = False,
        allowed_origins: list[str] | None = None,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
        streaming: bool = True,
        **kwargs: Any,
    ) -> type:
        """Create a configured DRF view class.

        Returning a class keeps DRF subclassing/mixin patterns ergonomic.
        """
        base_class = self.get_view_class(streaming=streaming)

        class ConfiguredView(base_class):
            pass

        ConfiguredView.run_agent = run_agent
        ConfiguredView.translate_event = translate_event
        ConfiguredView.get_system_message = get_system_message
        ConfiguredView.auth_required = auth_required
        ConfiguredView.allowed_origins = allowed_origins
        ConfiguredView.emit_run_lifecycle_events = emit_run_lifecycle_events
        ConfiguredView.error_detail_policy = error_detail_policy
        ConfiguredView.state_save_policy = state_save_policy

        for key, value in kwargs.items():
            setattr(ConfiguredView, key, value)

        return ConfiguredView

    def get_urlpatterns(
        self,
        path_prefix: str,
        run_agent: Callable[..., Any],
        streaming: bool = True,
        **kwargs: Any,
    ) -> list:
        """Build DRF URL patterns for one agent endpoint."""
        from django.urls import path

        view_class = self.create_view(
            run_agent=run_agent,
            streaming=streaming,
            **kwargs,
        )

        return [
            path(
                normalize_path_prefix(path_prefix),
                view_class.as_view(),
                name=build_route_name(self.route_name_prefix, path_prefix),
            )
        ]
