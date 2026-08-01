"""Experimentally set Q, W, and O letter mappings from the verified Q/W table.

O's adjacent empty entry is inferred from the verified Q and W entries.  This tool
is experimental until a physical O remap test succeeds.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from replay_q_letter_experimental import Q_TO_A_ENTRY, target_usage
from replay_sequence import load_outbound_packets

from fantech_he68.device import AtomHE68Pro


PACKETS_PER_UPDATE = 10
ENTRY_PACKET_INDEX = 2
Q_OFFSET = 28
W_OFFSET = 32
O_OFFSET = 60


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="EXPERIMENTAL: replay Q, W, and inferred O letter mappings.")
    result.add_argument("--q", default="M", help="target letter for Q (default: M)")
    result.add_argument("--w", default="M", help="target letter for W (default: M)")
    result.add_argument("--o", default="W", help="target letter for O (default: W)")
    result.add_argument("--recording", type=Path, default=Path("lighting/capture (8).json"), help="verified W-to-A recording")
    result.add_argument("--path", help="manual HIDAPI path")
    return result


def build_packets(recording: Path, *, q: str, w: str, o: str) -> list[bytes]:
    packets = load_outbound_packets(recording)
    if len(packets) != PACKETS_PER_UPDATE:
        raise ValueError(f"expected one {PACKETS_PER_UPDATE}-packet Q/W template, got {len(packets)} packets")
    packet = bytearray(packets[ENTRY_PACKET_INDEX])
    for key, offset, letter in (("Q", Q_OFFSET, q), ("W", W_OFFSET, w)):
        if bytes(packet[offset : offset + 4]) != Q_TO_A_ENTRY:
            raise ValueError(f"recording does not match the verified Q/W-to-A template at {key}")
        packet[offset + 2] = target_usage(letter)
    if bytes(packet[O_OFFSET : O_OFFSET + 4]) != b"\x00\x00\x00\x00":
        raise ValueError("recording does not have the expected empty inferred O entry")
    packet[O_OFFSET : O_OFFSET + 4] = bytes((0x02, 0x00, target_usage(o), 0x00))
    packets[ENTRY_PACKET_INDEX] = bytes(packet)
    return packets


def main() -> int:
    args = parser().parse_args()
    try:
        packets = build_packets(args.recording, q=args.q, w=args.w, o=args.o)
    except ValueError as error:
        parser.error(str(error))
    print(f"EXPERIMENTAL: replaying Q → {args.q.upper()}, W → {args.w.upper()}, O → {args.o.upper()}...", flush=True)
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
