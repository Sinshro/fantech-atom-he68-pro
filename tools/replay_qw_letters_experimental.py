"""Experimentally set Q and W letter mappings from the verified W-to-A table.

The W-to-A recording contains both Q-to-A and W-to-A entries, so this tool updates
both entries together and avoids silently resetting the other key to A.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from replay_q_letter_experimental import Q_TO_A_ENTRY, target_usage
from replay_sequence import load_outbound_packets

from fantech_he68.device import AtomHE68Pro


PACKETS_PER_UPDATE = 10
ENTRY_PACKET_INDEX = 2
ENTRY_OFFSETS = {"Q": 28, "W": 32}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="EXPERIMENTAL: replay Q and W letter mappings from the verified W-to-A template.")
    result.add_argument("--q", default="A", help="target letter for Q, A through Z (default: A)")
    result.add_argument("--w", default="A", help="target letter for W, A through Z (default: A)")
    result.add_argument("--recording", type=Path, default=Path("lighting/capture (8).json"), help="verified W-to-A recording")
    result.add_argument("--path", help="manual HIDAPI path")
    return result


def build_packets(recording: Path, *, q: str, w: str) -> list[bytes]:
    packets = load_outbound_packets(recording)
    if len(packets) != PACKETS_PER_UPDATE:
        raise ValueError(f"expected one {PACKETS_PER_UPDATE}-packet Q/W template, got {len(packets)} packets")
    packet = bytearray(packets[ENTRY_PACKET_INDEX])
    for key, letter in (("Q", q), ("W", w)):
        offset = ENTRY_OFFSETS[key]
        observed = bytes(packet[offset : offset + len(Q_TO_A_ENTRY)])
        if observed != Q_TO_A_ENTRY:
            raise ValueError(f"recording does not match the verified Q/W-to-A template at {key}")
        packet[offset + 2] = target_usage(letter)
    packets[ENTRY_PACKET_INDEX] = bytes(packet)
    return packets


def main() -> int:
    args = parser().parse_args()
    try:
        packets = build_packets(args.recording, q=args.q, w=args.w)
    except ValueError as error:
        parser.error(str(error))
    print(f"EXPERIMENTAL: replaying Q → {args.q.upper()}, W → {args.w.upper()}...", flush=True)
    keyboard = AtomHE68Pro()
    keyboard.connect(args.path)
    try:
        responses = [keyboard.send_observed_packet(packet) for packet in packets]
    finally:
        keyboard.disconnect()
    print(f"Experimental replay completed; received {len(responses)} unclassified device responses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
