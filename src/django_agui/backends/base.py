"""Base backend interface for django-agui.

All framework backends must implement this interface.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class AGUIBackend(Protocol):
    """Protocol for AG-UI framework backends.

    All framework implementations (DRF, Ninja, Bolt) must implement this.
    """

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
        **kwargs: Any,
    ) -> Any:
        """Create a view for this framework.

        Args:
            run_agent: Async function that runs the agent
            translate_event: Optional event translator
            get_system_message: Optional system message function
            auth_required: Whether authentication is required
            allowed_origins: CORS origins for this endpoint
            emit_run_lifecycle_events: Override lifecycle event emission
            error_detail_policy: "safe" or "full" RUN_ERROR payload policy
            state_save_policy: "always", "on_snapshot", or "disabled"
            **kwargs: Additional framework-specific options

        Returns:
            Framework-specific view callable or view class
        """
        ...

    def get_urlpatterns(
        self,
        path_prefix: str,
        run_agent: Callable[..., Any],
        **kwargs: Any,
    ) -> list:
        """Get URL patterns for this framework.

        Args:
            path_prefix: URL path prefix
            run_agent: Async function that runs the agent
            **kwargs: Additional options

        Returns:
            List of URL patterns
        """
        ...
