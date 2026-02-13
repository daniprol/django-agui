"""Django Ninja backend for django-agui."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django_agui.contrib.ninja.views import create_ninja_endpoint
from django_agui.urls import build_route_name, normalize_path_prefix


class NinjaBackend:
    """Backend helper for wiring AG-UI endpoints into Django Ninja."""

    route_name_prefix = "agui-ninja"

    def get_api_class(self):
        """Return the Ninja API class."""
        try:
            from ninja import NinjaAPI
        except ImportError as exc:
            raise ImportError(
                "Django Ninja is not installed. "
                "Install it with: pip install django-ninja"
            ) from exc
        return NinjaAPI

    def get_endpoint(
        self,
        *,
        run_agent: Callable[..., Any],
        translate_event: Callable[[Any], Any] | None = None,
        get_system_message: Callable[[Any], str | None] | None = None,
        auth_required: bool = False,
        allowed_origins: list[str] | None = None,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
    ) -> Callable[..., Any]:
        """Return the endpoint callable registered on the Ninja API."""
        return create_ninja_endpoint(
            run_agent=run_agent,
            translate_event=translate_event,
            get_system_message=get_system_message,
            auth_required=auth_required,
            allowed_origins=allowed_origins,
            emit_run_lifecycle_events=emit_run_lifecycle_events,
            error_detail_policy=error_detail_policy,
            state_save_policy=state_save_policy,
        )

    def create_api(
        self,
        run_agent: Callable[..., Any],
        translate_event: Callable[[Any], Any] | None = None,
        get_system_message: Callable[[Any], str | None] | None = None,
        auth_required: bool = False,
        allowed_origins: list[str] | None = None,
        emit_run_lifecycle_events: bool | None = None,
        error_detail_policy: str | None = None,
        state_save_policy: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create a NinjaAPI instance with one AG-UI endpoint at ``/``."""
        api = self.get_api_class()(**kwargs)
        api.post("/")(
            self.get_endpoint(
                run_agent=run_agent,
                translate_event=translate_event,
                get_system_message=get_system_message,
                auth_required=auth_required,
                allowed_origins=allowed_origins,
                emit_run_lifecycle_events=emit_run_lifecycle_events,
                error_detail_policy=error_detail_policy,
                state_save_policy=state_save_policy,
            )
        )
        return api

    def get_urlpatterns(
        self,
        path_prefix: str,
        run_agent: Callable[..., Any],
        **kwargs: Any,
    ) -> list:
        """Build Django URL patterns for a Ninja AG-UI endpoint."""
        from django.urls import path

        return [
            path(
                normalize_path_prefix(path_prefix),
                self.create_api(run_agent=run_agent, **kwargs).urls,
                name=build_route_name(self.route_name_prefix, path_prefix),
            )
        ]
