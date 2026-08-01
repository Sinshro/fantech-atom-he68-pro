"""Decode only documented HE68 PRO fields from a capture-backed packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fantech_he68.packetdb import decode_packet, load_byte_database, load_packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode documented fields from a 64-byte packet")
    parser.add_argument("packet", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    decoded = decode_packet(load_packet(args.packet), load_byte_database())
    if args.json:
        print(json.dumps(decoded, indent=2))
    else:
        print(f"Header: {decoded['header']}\nCommand: {decoded['command']}\nSubcommand: {decoded['subcommand']}\nFooter: {decoded['footer']}")
        for field in decoded["fields"]:
            print(f"Byte {field['offset']:2}: {field['value']}  {field['name']} ({field['confidence']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
