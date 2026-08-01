"""Capture-backed packet loading, decoding, comparison, and documentation helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .protocol import ACK_PREFIX, HOST_PREFIX, REPORT_LENGTH, TERMINATOR, TERMINATOR_OFFSET

CONFIDENCE_LEVELS = frozenset({"Verified", "High", "Medium", "Low", "Unknown"})


@dataclass(frozen=True, slots=True)
class ByteDefinition:
    offset: int
    name: str
    confidence: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class PacketDifference:
    offset: int
    before: int
    after: int
    name: str
    confidence: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_byte_database(path: Path | None = None) -> dict[int, ByteDefinition]:
    source = path or repository_root() / "database" / "bytes.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    definitions: dict[int, ByteDefinition] = {}
    for raw_offset, raw_definition in payload.items():
        offset = int(raw_offset)
        confidence = raw_definition["confidence"]
        if confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"invalid confidence {confidence!r} for byte {offset}")
        definitions[offset] = ByteDefinition(
            offset, raw_definition["name"], confidence, raw_definition.get("note", "")
        )
    return definitions


def load_packet(path: Path) -> bytes:
    """Load a 64-byte packet from a file or capture directory.

    A capture directory prefers `packet.bin`; `packet.json` is supported for
    reviewable source captures and contains `payload_hex`.
    """
    source = path / "packet.bin" if path.is_dir() and (path / "packet.bin").exists() else path
    if path.is_dir() and source == path:
        source = path / "packet.json" if (path / "packet.json").exists() else path / "session.json"
    if source.suffix.lower() == ".json":
        raw: Any = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            raw = raw[0]
        if "packets" in raw:
            try:
                raw = next(item for item in raw["packets"] if item["direction"] == "host_to_device")
            except (KeyError, StopIteration, TypeError) as error:
                raise ValueError(f"{source} has no host-to-device packet") from error
        try:
            packet = bytes.fromhex(raw["payload_hex"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{source} does not contain a valid payload_hex") from error
    else:
        packet = source.read_bytes()
    if len(packet) != REPORT_LENGTH:
        raise ValueError(f"{source} contains {len(packet)} bytes; expected {REPORT_LENGTH}")
    return packet


def compare_packets(before: bytes, after: bytes, definitions: dict[int, ByteDefinition]) -> list[PacketDifference]:
    if len(before) != REPORT_LENGTH or len(after) != REPORT_LENGTH:
        raise ValueError("packet comparisons require two 64-byte reports")
    differences: list[PacketDifference] = []
    for offset, (old, new) in enumerate(zip(before, after, strict=True)):
        if old != new:
            definition = definitions.get(offset, ByteDefinition(offset, "UNKNOWN", "Unknown"))
            differences.append(PacketDifference(offset, old, new, definition.name, definition.confidence))
    return differences


def decode_packet(packet: bytes, definitions: dict[int, ByteDefinition]) -> dict[str, object]:
    if len(packet) != REPORT_LENGTH:
        raise ValueError("decoder requires a 64-byte report")
    direction = "device_to_host" if packet.startswith(ACK_PREFIX) else "host_to_device"
    fields = [
        {
            "offset": offset,
            "value": f"{value:02X}",
            "name": definitions.get(offset, ByteDefinition(offset, "UNKNOWN", "Unknown")).name,
            "confidence": definitions.get(offset, ByteDefinition(offset, "UNKNOWN", "Unknown")).confidence,
        }
        for offset, value in enumerate(packet)
    ]
    return {
        "direction": direction,
        "header": f"{packet[0]:02X}",
        "command": f"{packet[1]:02X}",
        "subcommand": f"{packet[2]:02X}",
        "footer": packet[TERMINATOR_OFFSET : TERMINATOR_OFFSET + len(TERMINATOR)].hex().upper(),
        "has_verified_host_prefix": packet.startswith(HOST_PREFIX),
        "fields": fields,
    }
