"""Capture collection, validation, and capture-folder generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .capture import CaptureSession
from .protocol import ACK_PREFIX, REPORT_LENGTH

WEBSITE = "he68pro.driveall.cn"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    warnings: tuple[str, ...]
    tx_count: int
    rx_count: int
    has_single_request_ack_pair: bool


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not slug:
        raise ValueError("capture name must contain letters or numbers")
    return slug


def validate_session(session: CaptureSession) -> ValidationResult:
    packets = session.packets
    tx = [packet for packet in packets if packet.direction == "host_to_device"]
    rx = [packet for packet in packets if packet.direction == "device_to_host"]
    warnings: list[str] = []
    malformed = [packet.sequence for packet in packets if len(bytes.fromhex(packet.payload_hex)) != REPORT_LENGTH]
    if malformed:
        warnings.append(f"Malformed or unknown-length packets: {', '.join(map(str, malformed))}.")
    if not any(bytes.fromhex(packet.payload_hex).startswith(ACK_PREFIX) for packet in rx):
        warnings.append("No ACK observed.")
    if len(tx) != 1:
        warnings.append(f"Expected one request; observed {len(tx)}.")
    if len(rx) != 1:
        warnings.append(f"Expected one device response; observed {len(rx)}.")
    return ValidationResult(tuple(warnings), len(tx), len(rx), len(tx) == len(rx) == 1 and not warnings)


def session_from_web_recording(path: Path) -> CaptureSession:
    """Import the JSON downloaded by ``tools/webhid_recorder.js`` without inference."""
    document = json.loads(path.read_text(encoding="utf-8"))
    session = CaptureSession(str(document.get("capture_name", "webhid-capture")))
    for record in document.get("packets", []):
        payload = bytes.fromhex(record["payload_hex"])
        if record["direction"] == "host_to_device":
            session.record_outbound(payload)
        elif record["direction"] == "device_to_host":
            session.record_inbound(payload)
        else:
            raise ValueError(f"unknown packet direction: {record['direction']!r}")
    return session


def create_capture_folder(
    session: CaptureSession, *, root: Path, category: str, feature: str, capture_name: str,
    firmware: str = "unknown", action: str | None = None,
) -> tuple[Path, ValidationResult]:
    """Persist a fully self-contained capture and its generated companion files."""
    destination = root / slugify(category) / slugify(capture_name)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing capture: {destination}")
    destination.mkdir(parents=True)
    session.save(destination, stem="session")
    result = validate_session(session)
    metadata = {
        "category": slugify(category), "feature": slugify(feature), "capture_name": slugify(capture_name),
        "timestamp": datetime.now(UTC).isoformat(), "firmware": firmware, "website": WEBSITE,
        "verified": False, "validation_warnings": list(result.warnings),
    }
    (destination / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    notes = ["# Capture", "", "## Category", category.title(), "", "## Feature", feature.title(), "", "## Action", action or f"User selected {feature.title()} in official software.", "", "## Changed", "UNKNOWN", "", "## Status", "Captured"]
    if result.warnings:
        notes.extend(["", "## Validation", *[f"- Warning: {warning}" for warning in result.warnings]])
    (destination / "notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    return destination, result
