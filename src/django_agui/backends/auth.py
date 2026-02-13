"""Django authentication backend for AG-UI."""

from typing import Any


class DjangoAuthBackend:
    """Authentication backend that uses Django's authentication system."""

    def authenticate(self, request: Any) -> Any | None:
        """Authenticate using Django's request.user.

        Returns the user if authenticated, None otherwise.
        This is typically called after request processing,
        so the user should already be set on the request.
        """
        if hasattr(request, "user") and request.user.is_authenticated:
            return request.user
        return None

    def check_permission(self, user: Any, agent_path: str) -> bool:
        """Check if user has permission for the agent.

        By default, any authenticated user has access.
        Override this to implement custom permissions.
        """
        return user is not None
