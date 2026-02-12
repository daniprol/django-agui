"""Event encoder for SSE streaming."""

from ag_ui.core import BaseEvent
from ag_ui.encoder import EventEncoder as AGUIEventEncoder


class SSEEventEncoder:
    """Encoder for Server-Sent Events format."""

    def __init__(self) -> None:
        self._encoder = AGUIEventEncoder()

    def encode(self, event: BaseEvent) -> str:
        """Encode an AG-UI event to SSE format."""
        encoded = self._encoder.encode(event)
        return f"data: {encoded}\n\n"

    def encode_keepalive(self) -> str:
        """Encode a keepalive message."""
        return ": keepalive\n\n"
