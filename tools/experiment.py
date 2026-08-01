"""Compare two captures after recording the controlled variable changed."""

from __future__ import annotations

import argparse
from pathlib import Path

from fantech_he68.packetdb import compare_packets, load_byte_database, load_packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a controlled packet-comparison experiment")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("changed", type=Path)
    parser.add_argument("--what-changed", help="controlled setting, such as Brightness")
    args = parser.parse_args()
    changed = args.what_changed or input("What changed? ").strip()
    if not changed:
        parser.error("a controlled change description is required")
    differences = compare_packets(load_packet(args.baseline), load_packet(args.changed), load_byte_database())
    print(f"Controlled change: {changed}")
    if not differences:
        print("No packet bytes changed.")
        return 0
    for item in differences:
        print(f"Byte {item.offset}: {item.before:02X} -> {item.after:02X}; {item.name} ({item.confidence})")
    print("Interpretation remains TODO unless repeated controlled captures support it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
