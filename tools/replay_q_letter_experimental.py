"""Experimentally remap Q to an ASCII letter from the verified Q-to-A capture.

This is intentionally marked experimental: it derives the target letter's standard
USB HID keyboard usage from the verified Q-to-A table, rather than replaying a
separately captured target letter.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from replay_sequence import load_outbound_packets

from fantech_he68.device import AtomHE68Pro


PACKETS_PER_UPDATE = 10
Q_TO_A_ENTRY = bytes((0x02, 0x00, 0x04, 0x00))
ENTRY_PACKET_INDEX = 2
ENTRY_OFFSET = 28


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="EXPERIMENTAL: replay Q mapped to one letter using the verified Q-to-A template.")
    result.add_argument("letter", help="target letter, A through Z")
    result.add_argument("--recording", type=Path, default=Path("lighting/capture (7).json"), help="verified Q-to-A recording")
    result.add_argument("--path", help="manual HIDAPI path")
    return result


def target_usage(letter: str) -> int:
    if len(letter) != 1 or not letter.isascii() or not letter.isalpha():
        raise ValueError("letter must be one ASCII character from A through Z")
    return ord(letter.lower()) - ord("a") + 0x04


def build_packets(recording: Path, letter: str) -> list[bytes]:
    packets = load_outbound_packets(recording)
    if len(packets) != PACKETS_PER_UPDATE:
        raise ValueError(f"expected one {PACKETS_PER_UPDATE}-packet Q-to-A template, got {len(packets)} packets")
    packet = bytearray(packets[ENTRY_PACKET_INDEX])
    observed = bytes(packet[ENTRY_OFFSET : ENTRY_OFFSET + len(Q_TO_A_ENTRY)])
    if observed != Q_TO_A_ENTRY:
        raise ValueError("recording does not match the verified Q-to-A template at the expected entry")
    packet[ENTRY_OFFSET + 2] = target_usage(letter)
    packets[ENTRY_PACKET_INDEX] = bytes(packet)
    return packets


def main() -> int:
    args = parser().parse_args()
    try:
        packets = build_packets(args.recording, args.letter)
    except ValueError as error:
        parser.error(str(error))
    print(f"EXPERIMENTAL: replaying Q mapped to {args.letter.upper()} using the verified Q-to-A template...", flush=True)
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
