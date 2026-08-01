"""Replay an observed host packet and require the verified ACK prefix."""

from __future__ import annotations

import argparse
from pathlib import Path

from fantech_he68.device import AtomHE68Pro
from fantech_he68.packetdb import load_packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay a captured 64-byte host packet")
    parser.add_argument("capture", type=Path, help="packet.bin, packet.json, or a capture directory")
    parser.add_argument("--path", help="manual HIDAPI path")
    args = parser.parse_args()
    packet = load_packet(args.capture)
    keyboard = AtomHE68Pro()
    keyboard.connect(args.path)
    try:
        keyboard.send_packet(packet)
    finally:
        keyboard.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
