"""Conservative HID protocol support for the Fantech Atom HE68 PRO."""

from .device import AtomHE68Pro, DeviceNotFoundError, HidProtocolError

HE68Device = AtomHE68Pro

__all__ = ["AtomHE68Pro", "HE68Device", "DeviceNotFoundError", "HidProtocolError"]
