"""Protocol capability boundaries for future, capture-backed implementations."""

from __future__ import annotations


class UnsupportedProtocolFeature(NotImplementedError):
    """The requested behavior has no experimentally verified packet yet."""


class _CapturedCommandsOnly:
    def _unsupported(self, feature: str) -> None:
        raise UnsupportedProtocolFeature(
            f"TODO: {feature} requires an experimentally captured and validated command"
        )


class LightingProtocol(_CapturedCommandsOnly):
    """Static RGB is available on HE68Device; other lighting commands are TODO."""

    def set_effect(self, effect: str) -> None:
        self._unsupported(f"lighting effect {effect!r}")

    def set_brightness(self, percent: int) -> None:
        self._unsupported("brightness control")

    def set_per_key_colors(self, colors: object) -> None:
        self._unsupported("per-key RGB")


class PerformanceProtocol(_CapturedCommandsOnly):
    def configure(self, setting: str, value: object) -> None:
        self._unsupported(f"performance setting {setting!r}")


class MacroProtocol(_CapturedCommandsOnly):
    def upload(self, macro: object) -> None:
        self._unsupported("macro upload")


class ProfileProtocol(_CapturedCommandsOnly):
    def save(self, profile: object) -> None:
        self._unsupported("onboard profile save")


class FirmwareProtocol(_CapturedCommandsOnly):
    def update(self, image: bytes) -> None:
        self._unsupported("firmware update")
