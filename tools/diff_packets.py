"""Compare two capture-backed HE68 PRO packets without inferring new meanings."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path

from fantech_he68.packetdb import compare_packets, load_byte_database, load_packet


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Show changed bytes between two 64-byte HID packets")
    result.add_argument("capture1", type=Path)
    result.add_argument("capture2", type=Path)
    result.add_argument("--json", action="store_true", dest="as_json")
    result.add_argument("--markdown", action="store_true")
    result.add_argument("--html", action="store_true")
    return result


def render_text(differences: list[object]) -> str:
    return "\n\n".join(
        f"Byte {item.offset}\n{item.before:02X}\n↓\n{item.after:02X}\nMeaning: {item.name}\nConfidence: {item.confidence}"
        for item in differences
    ) or "No byte differences."


def render_markdown(differences: list[object]) -> str:
    rows = ["| Byte | Before | After | Meaning | Confidence |", "| --- | --- | --- | --- | --- |"]
    rows.extend(f"| {item.offset} | `{item.before:02X}` | `{item.after:02X}` | {item.name} | {item.confidence} |" for item in differences)
    return "\n".join(rows)


def render_html(differences: list[object]) -> str:
    rows = "".join(
        f"<tr><td>{item.offset}</td><td>{item.before:02X}</td><td>{item.after:02X}</td><td>{escape(item.name)}</td><td>{item.confidence}</td></tr>"
        for item in differences
    )
    return f"<table><thead><tr><th>Byte</th><th>Before</th><th>After</th><th>Meaning</th><th>Confidence</th></tr></thead><tbody>{rows}</tbody></table>"


def main() -> int:
    args = parser().parse_args()
    enabled = sum((args.as_json, args.markdown, args.html))
    if enabled > 1:
        parser().error("choose at most one output format")
    differences = compare_packets(load_packet(args.capture1), load_packet(args.capture2), load_byte_database())
    if args.as_json:
        print(json.dumps([item.as_dict() for item in differences], indent=2))
    elif args.markdown:
        print(render_markdown(differences))
    elif args.html:
        print(render_html(differences))
    else:
        print(render_text(differences))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
