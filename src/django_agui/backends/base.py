"""Base backend interface for django-agui.

All framework backends must implement this interface.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from ag_ui.core import RunAgentInput, BaseEvent


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
        **kwargs: Any,
    ) -> Any:
        """Create a view for this framework.

        Args:
            run_agent: Async function that runs the agent
            translate_event: Optional event translator
            get_system_message: Optional system message function
            auth_required: Whether authentication is required
            **kwargs: Additional framework-specific options

        Returns:
            View class or callable for this framework
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
