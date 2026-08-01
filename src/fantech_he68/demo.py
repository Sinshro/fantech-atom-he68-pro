"""Safe command-line interface for verified HE68 PRO capabilities."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from .capture import CaptureSession
from .device import AtomHE68Pro, HidProtocolError
from .framework import LightingProtocol, UnsupportedProtocolFeature

TRACE = 5
logging.addLevelName(TRACE, "TRACE")
LOG = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fantech Atom HE68 PRO reverse-engineering toolkit")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--red", action="store_true", help="set verified static red")
    action.add_argument("--green", action="store_true", help="set verified static green")
    action.add_argument("--blue", action="store_true", help="set verified static blue")
    action.add_argument("--rgb", nargs=3, type=_byte, metavar=("R", "G", "B"), help="set verified static RGB")
    action.add_argument("--capture", action="store_true", help="record incoming packets until Ctrl+C")
    action.add_argument("--listen", action="store_true", help="print incoming packets until Ctrl+C")
    action.add_argument("--effect", metavar="NAME", help="TODO: raises; no effect command is captured")
    action.add_argument("--brightness", type=int, metavar="PERCENT", help="TODO: raises; no brightness command is captured")
    action.add_argument("--speed", type=int, metavar="VALUE", help="TODO: raises; no speed command is captured")
    action.add_argument("--pc-sync", action="store_true", help="TODO: raises; no PC-sync command is captured")
    parser.add_argument("--path", help="manually specify a HIDAPI path if automatic detection fails")
    parser.add_argument("--capture-dir", type=Path, default=Path("captures"), help="directory for --capture output")
    parser.add_argument("--record-dir", type=Path, help="save this command's complete TX/RX capture session")
    parser.add_argument("--timeout-ms", type=_timeout, default=1_000, help="HID read timeout (default: 1000)")
    parser.add_argument("--log-level", choices=("TRACE", "DEBUG", "INFO"), default="INFO")
    parser.add_argument("--verbose", action="store_true", help="alias for --log-level DEBUG")
    return parser


def _byte(value: str) -> int:
    integer = int(value)
    if not 0 <= integer <= 255:
        raise argparse.ArgumentTypeError("must be between 0 and 255")
    return integer


def _timeout(value: str) -> int:
    integer = int(value)
    if integer < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return integer


def _configure_logging(args: argparse.Namespace) -> None:
    level = logging.DEBUG if args.verbose else getattr(logging, args.log_level)
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _color_from_args(args: argparse.Namespace) -> tuple[int, int, int] | None:
    if args.red:
        return (255, 0, 0)
    if args.green:
        return (0, 255, 0)
    if args.blue:
        return (0, 0, 255)
    return tuple(args.rgb) if args.rgb else None


def _capture(keyboard: AtomHE68Pro, session: CaptureSession, directory: Path, timeout_ms: int, print_packets: bool) -> int:
    LOG.info("Listening for HID packets; press Ctrl+C to stop")
    try:
        while True:
            try:
                packet = keyboard.receive_packet(timeout_ms)
            except HidProtocolError as error:
                if "Timed out" in str(error):
                    continue
                raise
            if print_packets:
                print(f"RECV {packet.hex().upper()}")
    except KeyboardInterrupt:
        if not print_packets:
            paths = session.save(directory)
            LOG.info("Saved %d packets: %s and %s", len(session.packets), paths.json_path, paths.binary_path)
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging(args)
    try:
        if args.effect:
            LightingProtocol().set_effect(args.effect)
        if args.brightness is not None:
            LightingProtocol().set_brightness(args.brightness)
        if args.speed is not None or args.pc_sync:
            raise UnsupportedProtocolFeature("TODO: no captured command exists for speed or PC sync")
        session = CaptureSession("demo-capture") if args.capture or args.listen or args.record_dir else None
        keyboard = AtomHE68Pro(ack_timeout_ms=args.timeout_ms, capture_session=session)
        keyboard.connect(args.path)
        try:
            if args.capture:
                assert session is not None
                return _capture(keyboard, session, args.capture_dir, args.timeout_ms, print_packets=False)
            if args.listen:
                assert session is not None
                return _capture(keyboard, session, args.capture_dir, args.timeout_ms, print_packets=True)
            color = _color_from_args(args)
            assert color is not None
            keyboard.set_color(*color)
            if args.record_dir is not None:
                assert session is not None
                paths = session.save(args.record_dir)
                LOG.info("Saved capture session: %s and %s", paths.json_path, paths.binary_path)
            return 0
        finally:
            keyboard.disconnect()
    except UnsupportedProtocolFeature as error:
        LOG.error("%s", error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
