"""Capture complete HID request/response sessions without modifying packets."""

from __future__ import annotations

import json
import struct
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

_BINARY_MAGIC = b"H68C"
_BINARY_VERSION = 1
_DIRECTION_CODE = {"host_to_device": 0, "device_to_host": 1}


@dataclass(slots=True)
class CapturedPacket:
    """One observed HID payload at the transport boundary."""

    sequence: int
    direction: str
    payload_hex: str
    timestamp: str
    paired_sequence: int | None = None


@dataclass(frozen=True, slots=True)
class CapturePaths:
    json_path: Path
    binary_path: Path


class CaptureSession:
    """Thread-safe ordered record of packets exchanged by one HID connection.

    A request is paired only after its response passes the device's ACK validation.
    Unsolicited and malformed inbound packets remain recorded but unpaired.
    """

    def __init__(self, label: str = "hid-session") -> None:
        self.session_id = str(uuid4())
        self.label = label
        self.started_at = datetime.now(UTC).isoformat()
        self._packets: list[CapturedPacket] = []
        self._pending_requests: list[int] = []
        self._last_inbound_sequence: int | None = None
        self._lock = Lock()

    @property
    def packets(self) -> tuple[CapturedPacket, ...]:
        with self._lock:
            return tuple(self._packets)

    def record_outbound(self, payload: bytes) -> CapturedPacket:
        return self._record("host_to_device", payload)

    def record_inbound(self, payload: bytes) -> CapturedPacket:
        record = self._record("device_to_host", payload)
        with self._lock:
            self._last_inbound_sequence = record.sequence
        return record

    def pair_latest_acknowledgement(self) -> tuple[CapturedPacket, CapturedPacket] | None:
        """Link the oldest unacknowledged request to the most recently received ACK."""
        with self._lock:
            if not self._pending_requests or self._last_inbound_sequence is None:
                return None
            request = self._packets[self._pending_requests.pop(0)]
            acknowledgement = self._packets[self._last_inbound_sequence]
            if acknowledgement.paired_sequence is not None:
                return None
            request.paired_sequence = acknowledgement.sequence
            acknowledgement.paired_sequence = request.sequence
            return request, acknowledgement

    def save(self, directory: Path, *, stem: str | None = None) -> CapturePaths:
        """Write JSON and a lossless, direction/timestamp-aware binary session."""
        directory.mkdir(parents=True, exist_ok=True)
        stem = stem or f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{self.session_id[:8]}"
        json_path = directory / f"{stem}.json"
        binary_path = directory / f"{stem}.bin"
        records = self.packets
        document = {
            "format": "fantech_he68.capture.v1",
            "session_id": self.session_id,
            "label": self.label,
            "started_at": self.started_at,
            "packets": [asdict(record) for record in records],
        }
        json_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
        with binary_path.open("wb") as output:
            output.write(_BINARY_MAGIC)
            output.write(bytes((_BINARY_VERSION,)))
            output.write(struct.pack("<I", len(records)))
            for record in records:
                payload = bytes.fromhex(record.payload_hex)
                timestamp_ns = int(datetime.fromisoformat(record.timestamp).timestamp() * 1_000_000_000)
                paired_sequence = record.paired_sequence if record.paired_sequence is not None else -1
                output.write(struct.pack("<IBqiiH", record.sequence, _DIRECTION_CODE[record.direction], timestamp_ns, paired_sequence, len(payload), 0))
                output.write(payload)
        return CapturePaths(json_path, binary_path)

    def _record(self, direction: str, payload: bytes) -> CapturedPacket:
        if direction not in _DIRECTION_CODE:
            raise ValueError(f"unknown capture direction: {direction}")
        with self._lock:
            record = CapturedPacket(
                sequence=len(self._packets),
                direction=direction,
                payload_hex=payload.hex().upper(),
                timestamp=datetime.now(UTC).isoformat(),
            )
            self._packets.append(record)
            if direction == "host_to_device":
                self._pending_requests.append(record.sequence)
            return record
