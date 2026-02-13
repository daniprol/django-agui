"""Event encoder for SSE streaming."""

from ag_ui.core import BaseEvent


class SSEEventEncoder:
    """Encoder for Server-Sent Events format."""

    def encode(self, event: BaseEvent) -> str:
        """Encode an AG-UI event to SSE format."""
        return f"data: {event.model_dump_json(by_alias=True, exclude_none=True)}\n\n"

    def encode_keepalive(self) -> str:
        """Encode a keepalive message."""
        return ": keepalive\n\n"
