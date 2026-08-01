"""Future integrations which must use only verified device capabilities."""

from __future__ import annotations

from typing import Protocol


class RealtimeRgbAdapter(Protocol):
    """Host-integration boundary for a future OpenRGB or SignalRGB adapter.

    Implementations must not send frames until a streaming packet format has been
    experimentally captured. The current static-colour command is not presumed to
    be safe or performant for real-time streaming.
    """

    def set_static_color(self, red: int, green: int, blue: int) -> None: ...
