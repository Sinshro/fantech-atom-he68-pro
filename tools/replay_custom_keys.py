"""Replay one complete observed Custom Keys mapping update."""

from __future__ import annotations

import argparse
from pathlib import Path

from replay_sequence import load_outbound_packets

from fantech_he68.device import AtomHE68Pro


PACKETS_PER_UPDATE = 10


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Replay one complete captured Custom Keys update.")
    result.add_argument("recording", type=Path, nargs="?", default=Path("lighting/capture (7).json"))
    result.add_argument("--group", type=int, help="1-based update group (default: the final complete update)")
    result.add_argument("--path", help="manual HIDAPI path")
    return result


def main() -> int:
    args = parser().parse_args()
    packets = load_outbound_packets(args.recording)
    if len(packets) % PACKETS_PER_UPDATE:
        parser.error(f"recording has {len(packets)} packets; expected a multiple of {PACKETS_PER_UPDATE}")
    group_count = len(packets) // PACKETS_PER_UPDATE
    group = args.group or group_count
    if not 1 <= group <= group_count:
        parser.error(f"--group must be between 1 and {group_count}")

    start = (group - 1) * PACKETS_PER_UPDATE
    selected = packets[start : start + PACKETS_PER_UPDATE]
    print(f"Replaying Custom Keys update {group}/{group_count} ({len(selected)} packets)...", flush=True)
    keyboard = AtomHE68Pro()
    keyboard.connect(args.path)
    try:
        responses = [keyboard.send_observed_packet(packet) for packet in selected]
    finally:
        keyboard.disconnect()
    print(f"Custom Keys update replayed; received {len(responses)} unclassified device responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
