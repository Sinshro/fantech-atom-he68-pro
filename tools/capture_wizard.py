"""Interactive, capture-first workflow for WebHID recordings."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from fantech_he68.capture import CaptureSession
from fantech_he68.collection import create_capture_folder, session_from_web_recording

CATEGORIES = ("lighting", "performance", "macros", "settings", "custom_keys")


def choose(title: str, choices: tuple[str, ...]) -> str:
    print(f"\n{title}")
    for index, value in enumerate(choices, 1):
        print(f"  {index}. {value.replace('_', ' ').title()}")
    while True:
        answer = input("> ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]
        if answer in choices:
            return answer
        print("Choose a listed number or value.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Turn a WebHID recording into an organized capture.")
    parser.add_argument("--recording", type=Path, help="JSON automatically downloaded by webhid_recorder.js")
    parser.add_argument("--category", choices=CATEGORIES)
    parser.add_argument("--feature")
    parser.add_argument("--name")
    parser.add_argument("--packet-index", type=int, help="1-based packet to extract from a batch recording")
    parser.add_argument("--root", type=Path, default=Path("captures"))
    parser.add_argument("--firmware", default="unknown")
    args = parser.parse_args()
    category = args.category or choose("Category", CATEGORIES)
    feature = args.feature or input("Feature (for example Dynamic Breathing): ").strip()
    name = args.name or input(f"Capture name [{feature}]: ").strip() or feature
    if not feature or not name:
        parser.error("feature and capture name are required")
    if args.recording:
        recording = args.recording
    else:
        print("\nOpen the official software. Paste tools/webhid_recorder.js into DevTools once, then click Start Recording.")
        input("When ready press ENTER. ")
        print("Perform ONE action in the official software. Waiting for the recorder download; press Ctrl+C to cancel.")
        recording = wait_for_web_recording()
    if recording is None:
        parser.error("no downloaded WebHID recording found; rerun with --recording PATH")
    print(f"Using downloaded recording: {recording.name}")
    session = session_from_web_recording(recording)
    if args.packet_index is not None:
        if not 1 <= args.packet_index <= len(session.packets):
            parser.error(f"--packet-index must be between 1 and {len(session.packets)}")
        observed = session.packets[args.packet_index - 1]
        session = CaptureSession(name)
        payload = bytes.fromhex(observed.payload_hex)
        if observed.direction == "host_to_device":
            session.record_outbound(payload)
        else:
            session.record_inbound(payload)
    output, validation = create_capture_folder(session, root=args.root, category=category, feature=feature,
                                                capture_name=name, firmware=args.firmware)
    print(f"Saved {output}")
    if validation.warnings:
        print("Warnings:\n- " + "\n- ".join(validation.warnings))
    candidates = sorted(path for path in args.root.glob("*/*") if path != output and (path / "session.json").exists())
    if candidates and input("Compare against a previous capture? [y/N] ").strip().lower() == "y":
        for index, path in enumerate(candidates, 1): print(f"  {index}. {path}")
        selected = candidates[int(input("> ")) - 1]
        diff = subprocess.run([sys.executable, "tools/diff_packets.py", str(selected), str(output), "--markdown"],
                              check=True, capture_output=True, text=True)
        (output / "diff.md").write_text(diff.stdout, encoding="utf-8")
    subprocess.run([sys.executable, "tools/generate_docs.py"], check=True)
    return 0


def newest_web_recording(*, modified_after: float = 0) -> Path | None:
    """Find the recorder's latest automatic download without moving or renaming it."""
    downloads = Path.home() / "Downloads"
    recordings = [path for path in downloads.glob("*.json") if path.stat().st_mtime >= modified_after] if downloads.exists() else []
    return max(recordings, key=lambda path: path.stat().st_mtime, default=None)


def wait_for_web_recording() -> Path | None:
    """Wait until the recorder's automatic download appears in Downloads."""
    started = time.time()
    while True:
        recording = newest_web_recording(modified_after=started)
        if recording is not None:
            # Chromium may expose the final name before it has finished writing.
            time.sleep(0.3)
            return recording
        time.sleep(0.5)


if __name__ == "__main__":
    raise SystemExit(main())
