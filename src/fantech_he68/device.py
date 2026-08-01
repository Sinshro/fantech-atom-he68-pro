"""HIDAPI transport for the verified Fantech Atom HE68 PRO protocol."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any, Protocol

from .protocol import (
    PRODUCT_ID,
    KNOWN_STATIC_COLOR_TEMPLATE,
    REPORT_ID,
    REPORT_LENGTH,
    USAGE_PAGE,
    VENDOR_ID,
    RgbColor,
    build_set_color_packet,
    is_ack_for,
)
from .capture import CaptureSession

LOG = logging.getLogger(__name__)


class HidDevice(Protocol):
    def open_path(self, path: bytes) -> None: ...

    def close(self) -> None: ...

    def write(self, data: bytes) -> int: ...

    def read(self, max_length: int, timeout_ms: int = 0) -> list[int]: ...


class HidModule(Protocol):
    def enumerate(self, vendor_id: int, product_id: int) -> list[Mapping[str, Any]]: ...

    def device(self) -> HidDevice: ...


class DeviceNotFoundError(RuntimeError):
    """Raised when no HE68 PRO vendor-defined HID interface is available."""


class HidProtocolError(RuntimeError):
    """Raised for malformed writes, timeouts, or invalid device acknowledgements."""


def _hex(data: bytes) -> str:
    return data.hex(" ").upper()


class AtomHE68Pro:
    """Connection to the HE68 PRO vendor-defined HID interface.

    The target interface is selected by VID, PID, and the verified vendor usage page
    ``0xFF68``. HIDAPI does not expose report descriptor details consistently across
    platforms, so the known one-input/one-output-report property cannot be queried
    here; the usage-page match is the non-guessing discriminator available to HIDAPI.
    """

    def __init__(
        self,
        *,
        hid_module: HidModule | None = None,
        color_packet_template: bytes = KNOWN_STATIC_COLOR_TEMPLATE,
        ack_timeout_ms: int = 1_000,
        capture_session: CaptureSession | None = None,
    ) -> None:
        if ack_timeout_ms < 0:
            raise ValueError("ack_timeout_ms must be non-negative")
        self._hid_module = hid_module
        self._device: HidDevice | None = None
        self._color_packet_template = color_packet_template
        self._ack_timeout_ms = ack_timeout_ms
        self.capture_session = capture_session

    @property
    def connected(self) -> bool:
        return self._device is not None

    def connect(self, path: bytes | str | None = None) -> None:
        """Find and open the verified vendor-defined HID interface."""
        if self._device is not None:
            return
        hid_module = self._hid_module or _import_hidapi()
        candidates = hid_module.enumerate(VENDOR_ID, PRODUCT_ID)
        matches = [item for item in candidates if item.get("usage_page") == USAGE_PAGE]
        LOG.debug("HID candidates: %s; matching usage page 0x%04X: %d", len(candidates), USAGE_PAGE, len(matches))
        if path is not None:
            selected_path = os.fsencode(path) if isinstance(path, str) else path
            LOG.warning("Opening manually specified HID path; VID/PID/usage page were not verified")
        elif not matches:
            raise DeviceNotFoundError(
                "No Fantech Atom HE68 PRO HID interface found with usage page 0xFF68. "
                "Check the USB connection and HID permissions."
            )
        elif len(matches) > 1:
            raise DeviceNotFoundError(
                "More than one matching HE68 PRO vendor interface was found; refusing to guess."
            )
        elif not isinstance(matches[0].get("path"), bytes):
            raise DeviceNotFoundError("Matching HID interface has no usable HIDAPI path")
        else:
            selected_path = matches[0]["path"]
        device = hid_module.device()
        try:
            device.open_path(selected_path)
        except Exception:
            device.close()
            raise
        self._hid_module = hid_module
        self._device = device
        LOG.info("Connected to HE68 PRO interface: %r", selected_path)

    def disconnect(self) -> None:
        """Close the HIDAPI handle. Safe to call repeatedly."""
        if self._device is not None:
            self._device.close()
            self._device = None
            LOG.info("Disconnected from HE68 PRO")

    def __enter__(self) -> "AtomHE68Pro":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.disconnect()

    def set_color(self, red: int, green: int, blue: int) -> bytes:
        """Send a verified RGB command and require its verified ACK."""
        packet = build_set_color_packet(RgbColor(red, green, blue), self._color_packet_template)
        return self.send_packet(packet)

    def send_packet(self, packet: bytes) -> bytes:
        """Send one 64-byte report and return a validated acknowledgement.

        HIDAPI's ``write`` includes the report ID as byte zero, unlike WebHID's
        ``sendReport(report_id, data)``. The wire payload remains exactly 64 bytes.
        """
        self._write_packet(packet)
        return self.wait_ack()

    def send_observed_packet(self, packet: bytes) -> bytes:
        """Send an observed report and return its response without interpreting it.

        This is for capture replay where the response format has not been verified.
        Unlike :meth:`send_packet`, no response prefix is asserted or inferred.
        """
        self._write_packet(packet)
        return self.receive_packet()

    def send_packet_no_response(self, packet: bytes) -> None:
        """Send an observed report when the action deliberately disconnects HID.

        Return-rate changes can re-enumerate the keyboard before a response can be
        read, so waiting for a packet would turn a successful write into a timeout.
        """
        self._write_packet(packet)

    def _write_packet(self, packet: bytes) -> None:
        """Write one wire payload while preserving it in the optional capture session."""
        if len(packet) != REPORT_LENGTH:
            raise ValueError(f"packet must be exactly {REPORT_LENGTH} bytes")
        device = self._require_device()
        transport_packet = bytes((REPORT_ID,)) + packet
        LOG.debug("TX report_id=%d payload[%d]: %s", REPORT_ID, len(packet), _hex(packet))
        if self.capture_session is not None:
            self.capture_session.record_outbound(packet)
        written = device.write(transport_packet)
        if written != len(transport_packet):
            raise HidProtocolError(
                f"HID write was incomplete: wrote {written}, expected {len(transport_packet)} bytes"
            )

    def receive_packet(self, timeout_ms: int | None = None) -> bytes:
        """Read one incoming HID packet and normalize an optional report-ID byte."""
        device = self._require_device()
        effective_timeout = self._ack_timeout_ms if timeout_ms is None else timeout_ms
        raw = bytes(device.read(REPORT_LENGTH + 1, effective_timeout))
        if not raw:
            raise HidProtocolError(f"Timed out waiting {effective_timeout} ms for HE68 PRO packet")
        packet = self._strip_report_id(raw)
        LOG.debug("RECV raw[%d]: %s", len(raw), _hex(raw))
        LOG.debug("RECV payload[%d]: %s", len(packet), _hex(packet))
        if self.capture_session is not None:
            self.capture_session.record_inbound(packet)
        return packet

    def wait_ack(self) -> bytes:
        """Read, log, normalize, and validate the ACK starting ``55 23 10``."""
        packet = self.receive_packet()
        if not is_ack_for(packet):
            raise HidProtocolError(f"Unexpected HE68 PRO response; expected 55 23 10, got {_hex(packet)}")
        if self.capture_session is not None:
            self.capture_session.pair_latest_acknowledgement()
        LOG.info("Received valid HE68 PRO ACK beginning 55 23 10")
        return packet

    def read_ack(self) -> bytes:
        """Backward-compatible alias for :meth:`wait_ack`."""
        return self.wait_ack()

    def read_state(self) -> bytes:
        """Read state is not implemented: no read-state command has been captured."""
        raise NotImplementedError("TODO: capture and validate a read-state command")

    @staticmethod
    def _strip_report_id(raw: bytes) -> bytes:
        """Normalize HIDAPI reads that include report ID zero.

        The first byte is stripped only for a 65-byte response whose leading byte is
        the known report ID. A 64-byte response beginning ``55`` is never altered.
        """
        if len(raw) == REPORT_LENGTH + 1 and raw[0] == REPORT_ID:
            return raw[1:]
        return raw

    def _require_device(self) -> HidDevice:
        if self._device is None:
            raise HidProtocolError("Not connected; call connect() first")
        return self._device


def _import_hidapi() -> HidModule:
    try:
        import hid  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("hidapi is required; install it with: py -m pip install hidapi") from error
    return hid  # type: ignore[return-value]
