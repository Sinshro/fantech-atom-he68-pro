"""Brief, reversible RGB stress test for a wired Fantech Atom HE68 PRO."""

from __future__ import annotations

import argparse
import time

from fantech_he68.device import AtomHE68Pro


COLORS = (
    (255, 0, 0),
    (0, 255, 0),
    (0, 80, 255),
    (255, 0, 180),
    (255, 255, 255),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapidly cycle wired HE68 RGB colours.")
    parser.add_argument("--seconds", type=float, default=15.0, help="test duration (default: 15)")
    parser.add_argument("--delay", type=float, default=0.15, help="seconds between colours (default: 0.15)")
    args = parser.parse_args()
    if args.seconds <= 0 or args.delay < 0:
        parser.error("--seconds must be positive and --delay cannot be negative")

    changes = 0
    started = time.monotonic()
    with AtomHE68Pro(ack_timeout_ms=1_000) as keyboard:
        try:
            while time.monotonic() - started < args.seconds:
                keyboard.set_color(*COLORS[changes % len(COLORS)])
                changes += 1
                time.sleep(args.delay)
        except KeyboardInterrupt:
            print("Stopped by user.")
    print(f"Completed {changes} colour changes in {time.monotonic() - started:.1f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
