"""Replay all observed commands in an Advanced Settings capture."""

from __future__ import annotations

import argparse
from pathlib import Path

from replay_sequence import load_outbound_packets

from fantech_he68.device import AtomHE68Pro


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Replay each observed Advanced Settings command in capture order."
    )
    result.add_argument("recording", type=Path, help="WebHID JSON recording to replay")
    result.add_argument("--path", help="manual HIDAPI path")
    return result


def main() -> int:
    args = parser().parse_args()
    packets = load_outbound_packets(args.recording)
    print(f"Replaying {len(packets)} observed Advanced Settings command(s)...", flush=True)
    keyboard = AtomHE68Pro()
    keyboard.connect(args.path)
    try:
        responses = [keyboard.send_observed_packet(packet) for packet in packets]
    finally:
        keyboard.disconnect()
    print(f"Replay completed; received {len(responses)} unclassified device responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
