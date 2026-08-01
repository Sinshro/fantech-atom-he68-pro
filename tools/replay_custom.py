"""Replay one complete multi-packet Custom lighting update."""

from __future__ import annotations

import argparse
from pathlib import Path

from replay_sequence import load_outbound_packets

from fantech_he68.device import AtomHE68Pro

PACKETS_PER_CUSTOM_UPDATE = 10


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Replay one complete Custom lighting update.")
    result.add_argument("recording", type=Path, nargs="?", default=Path("lighting/capture (1).json"))
    result.add_argument("--group", type=int, default=1, help="1-based Custom update group (default: 1)")
    result.add_argument("--select-custom", action="store_true", help="select Custom mode before applying the update")
    result.add_argument("--mode-recording", type=Path, default=Path("lighting/capture.json"), help="lighting-mode batch recording")
    result.add_argument("--mode-index", type=int, default=19, help="1-based Custom-mode selection packet in --mode-recording")
    result.add_argument("--path", help="manual HIDAPI path")
    return result


def main() -> int:
    args = parser().parse_args()
    packets = load_outbound_packets(args.recording)
    if len(packets) % PACKETS_PER_CUSTOM_UPDATE:
        parser.error(f"recording has {len(packets)} packets; expected a multiple of {PACKETS_PER_CUSTOM_UPDATE}")
    group_count = len(packets) // PACKETS_PER_CUSTOM_UPDATE
    if not 1 <= args.group <= group_count:
        parser.error(f"--group must be between 1 and {group_count}")
    start = (args.group - 1) * PACKETS_PER_CUSTOM_UPDATE
    selected = packets[start : start + PACKETS_PER_CUSTOM_UPDATE]

    print(f"Replaying Custom update {args.group}/{group_count} ({len(selected)} packets)...", flush=True)
    keyboard = AtomHE68Pro()
    keyboard.connect(args.path)
    try:
        if args.select_custom:
            mode_packets = load_outbound_packets(args.mode_recording)
            if not 1 <= args.mode_index <= len(mode_packets):
                parser.error(f"--mode-index must be between 1 and {len(mode_packets)}")
            print("Selecting Custom mode...", flush=True)
            # This packet is an observed UI selection. It uses the existing verified
            # standard-mode ACK path; the Custom table responses stay unclassified.
            keyboard.send_packet(mode_packets[args.mode_index - 1])
        responses: list[bytes] = []
        for packet in selected:
            responses.append(keyboard.send_observed_packet(packet))
    finally:
        keyboard.disconnect()
    print(f"Custom update replayed; received {len(responses)} unclassified device responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
