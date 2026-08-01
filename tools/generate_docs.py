"""Generate capture-linked protocol documentation from the capture database."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    commands = json.loads((root / "database" / "commands.json").read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for command in commands:
        grouped[str(command["category"])].append(command)
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    for category in ("lighting", "performance", "macros", "profiles", "settings", "custom_keys"):
        lines = [f"# {category.title()} protocol", "", "Generated from `database/commands.json`. Do not edit by hand.", ""]
        entries = grouped.get(category, [])
        if not entries:
            lines.extend(["No verified commands are recorded.", ""])
        for entry in entries:
            lines.extend([f"## {entry['name']}", "", f"- Verified: `{entry['verified']}`", f"- Command/subcommand: `{entry['command']}` / `{entry['subcommand']}`", "- Captures:"])
            lines.extend(f"  - [{capture}](../{capture})" for capture in entry["captures"])
            lines.append("")
        (docs / f"{category}.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
