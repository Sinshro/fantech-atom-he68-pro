"""Replay each host packet in a WebHID batch capture with a visible pause."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from fantech_he68.device import AtomHE68Pro
from fantech_he68.protocol import REPORT_LENGTH


def load_outbound_packets(recording: Path) -> list[bytes]:
    """Read observed outbound packets only; no packet fields are interpreted."""
    document = json.loads(recording.read_text(encoding="utf-8"))
    try:
        packets = [
            bytes.fromhex(record["payload_hex"])
            for record in document["packets"]
            if record["direction"] == "host_to_device"
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{recording} is not a valid WebHID capture") from error
    invalid = [index for index, packet in enumerate(packets, 1) if len(packet) != REPORT_LENGTH]
    if invalid:
        raise ValueError(f"packets with unexpected length at positions: {invalid}")
    if not packets:
        raise ValueError("recording contains no host-to-device packets")
    return packets


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Replay each observed packet and pause between effects.")
    result.add_argument("recording", type=Path, nargs="?", default=Path("lighting/capture.json"))
    result.add_argument("--delay", type=float, default=5.0, help="seconds to show each effect (default: 5)")
    result.add_argument("--path", help="manual HIDAPI path")
    result.add_argument("--start", type=int, default=1, help="first 1-based packet index")
    result.add_argument("--end", type=int, help="last 1-based packet index, inclusive")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.delay < 0:
        parser.error("--delay must not be negative")
    packets = load_outbound_packets(args.recording)
    end = args.end or len(packets)
    if not 1 <= args.start <= end <= len(packets):
        parser.error(f"--start/--end must be within 1..{len(packets)}")

    keyboard = AtomHE68Pro()
    keyboard.connect(args.path)
    try:
        for index in range(args.start, end + 1):
            print(f"[{index}/{len(packets)}] Replaying observed packet; holding for {args.delay:g} seconds...", flush=True)
            keyboard.send_packet(packets[index - 1])
            if index < end:
                time.sleep(args.delay)
    finally:
        keyboard.disconnect()
    print("Replay sequence completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
