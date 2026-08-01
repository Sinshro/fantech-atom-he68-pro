"""Safely replay a captured keyboard Return Rate change."""

from __future__ import annotations

import argparse
from pathlib import Path

from replay_sequence import load_outbound_packets

from fantech_he68.device import AtomHE68Pro


RECORDINGS = {
    "1k": Path("lighting/1k.json"),
    "4k": Path("lighting/4k.json"),
    "8k": Path("lighting/8k.json"),
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Replay one captured Return Rate command; the keyboard will reconnect.")
    result.add_argument("rate", choices=RECORDINGS, help="captured Return Rate to apply")
    result.add_argument("--confirm-disconnect", action="store_true", help="required acknowledgement that USB HID will reconnect")
    result.add_argument("--path", help="manual HIDAPI path")
    return result


def main() -> int:
    args = parser().parse_args()
    if not args.confirm_disconnect:
        parser.error("--confirm-disconnect is required because this setting re-enumerates the keyboard")
    packets = load_outbound_packets(RECORDINGS[args.rate])
    if len(packets) != 1:
        parser.error(f"expected one Return Rate command in {RECORDINGS[args.rate]}, got {len(packets)}")
    print(f"Applying captured {args.rate.upper()} Return Rate; the keyboard will briefly disconnect...", flush=True)
    keyboard = AtomHE68Pro()
    keyboard.connect(args.path)
    try:
        keyboard.send_packet_no_response(packets[0])
    finally:
        keyboard.disconnect()
    print("Command sent. Wait a few seconds for Windows and the official software to reconnect to the keyboard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
