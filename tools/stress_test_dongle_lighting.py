"""Safely stress-test HE68 PRO 2.4 GHz Custom Lighting transport.

This is a lighting/USB stability test only. It uses the 32-byte Custom-table
format and 26 ms inter-report delay captured from the official wireless app.
It never sends key presses, firmware commands, or performance settings.
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Iterable

from fantech_he68.custom_lighting import (
    KEYBOARD_ROWS,
    WIRELESS_ENTRIES_PER_PACKET,
    WIRELESS_REPORT_LENGTH,
    blank_table,
    build_custom_frame,
)
from fantech_he68.protocol import (
    BATTERY_QUERY_PACKET,
    WIRELESS_REPORT_LENGTH as BATTERY_RESPONSE_LENGTH,
    decode_battery_percentage,
)

VENDOR_ID = 0x0C45
DONGLE_PRODUCT_ID = 0xFEFE
DONGLE_USAGE_PAGE = 0xFF60
DONGLE_USAGE = 0x61
REPORT_ID = 0
PACKET_DELAY_SECONDS = 0.026
RAPID_STATIC_DELAY_SECONDS = 0.10


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Stress-test HE68 PRO dongle RGB transport.")
    result.add_argument("--seconds", type=float, default=60.0, help="test duration (default: 60)")
    result.add_argument("--path", help="manual HIDAPI path")
    result.add_argument("--rapid-static", action="store_true", help="rapid full-keyboard colour switching (10 Hz)")
    result.add_argument("--battery", action="store_true", help="read and print the captured battery percentage, then exit")
    return result


def _find_dongle_path(hid: object) -> bytes:
    candidates = [
        item
        for item in hid.enumerate()
        if item.get("vendor_id") == VENDOR_ID
        and item.get("product_id") == DONGLE_PRODUCT_ID
        and item.get("usage_page") == DONGLE_USAGE_PAGE
        and item.get("usage") == DONGLE_USAGE
        and isinstance(item.get("path"), bytes)
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected exactly one HE68 dongle RGB interface (found {len(candidates)}); "
            "close SignalRGB/official software or pass --path"
        )
    return candidates[0]["path"]


def _rainbow_table(phase: int) -> list[tuple[int, int, int]]:
    palette = ((255, 0, 0), (255, 120, 0), (255, 255, 0), (0, 255, 0), (0, 80, 255), (130, 0, 255))
    table = blank_table()
    for row in KEYBOARD_ROWS:
        for column, address in enumerate(row):
            table[address] = palette[(column + phase) % len(palette)]
    return table


def _send_frame(device: object, packets: Iterable[bytes]) -> int:
    writes = 0
    for packet in packets:
        written = device.write(bytes((REPORT_ID,)) + packet)
        if written != WIRELESS_REPORT_LENGTH + 1:
            raise RuntimeError(f"incomplete HID write: {written}, expected {WIRELESS_REPORT_LENGTH + 1}")
        writes += 1
        time.sleep(PACKET_DELAY_SECONDS)
    return writes


def _static_color_packet(red: int, green: int, blue: int) -> bytes:
    """Build the captured 32-byte wireless Static Bright command."""
    packet = bytearray.fromhex(
        "AA 23 10 00 00 00 01 00 01 FF FF FF FF 00 00 00 "
        "01 05 04 00 00 00 AA 55 00 00 00 00 00 00 00 00"
    )
    packet[9:12] = bytes((red, green, blue))
    return bytes(packet)


def _read_battery_percentage(device: object) -> int:
    """Run the capture-verified wireless battery query without changing settings."""
    # The receiver retains acknowledgements for prior Custom-lighting frames.
    # Discard those stale 55 24 replies before issuing a request that needs its
    # own 55 10 18 response.
    for _ in range(256):
        if not device.read(BATTERY_RESPONSE_LENGTH + 1, 0):
            break
    written = device.write(bytes((REPORT_ID,)) + BATTERY_QUERY_PACKET)
    if written != WIRELESS_REPORT_LENGTH + 1:
        raise RuntimeError(f"incomplete battery query: wrote {written}, expected {WIRELESS_REPORT_LENGTH + 1}")
    deadline = time.monotonic() + 1.0
    last_response = b""
    while time.monotonic() < deadline:
        remaining_ms = max(1, int((deadline - time.monotonic()) * 1_000))
        raw = bytes(device.read(BATTERY_RESPONSE_LENGTH + 1, remaining_ms))
        if not raw:
            continue
        if len(raw) == BATTERY_RESPONSE_LENGTH + 1 and raw[0] == REPORT_ID:
            raw = raw[1:]
        last_response = raw
        if raw.startswith(bytes.fromhex("55 10 18")):
            return decode_battery_percentage(raw)
    detail = last_response.hex(" ").upper() if last_response else "no response"
    raise RuntimeError(f"battery query timed out; last receiver response: {detail}")


def main() -> int:
    args = parser().parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be greater than zero")
    try:
        import hid  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("hidapi is required; install it with: py -m pip install hidapi") from error

    path = args.path.encode() if args.path else _find_dongle_path(hid)
    device = hid.device()
    device.open_path(path)
    started = time.monotonic()
    writes = 0
    frames = 0
    try:
        if args.battery:
            print(f"Battery: {_read_battery_percentage(device)}%")
        elif args.rapid_static:
            print(f"Rapid static-colour test for {args.seconds:g}s at 10 Hz...", flush=True)
            colors = ((255, 0, 0), (0, 255, 0), (0, 80, 255), (255, 0, 180), (255, 255, 255))
            while time.monotonic() - started < args.seconds:
                packet = _static_color_packet(*colors[frames % len(colors)])
                writes += _send_frame(device, (packet,))
                frames += 1
                time.sleep(max(0, RAPID_STATIC_DELAY_SECONDS - PACKET_DELAY_SECONDS))
                print(f"{frames} rapid colour changes / {writes} successful reports", end="\r", flush=True)
        else:
            print(f"Stress testing dongle RGB for {args.seconds:g}s at the observed safe pacing...", flush=True)
            while time.monotonic() - started < args.seconds:
                packets = build_custom_frame(
                    _rainbow_table(frames),
                    entries_per_packet=WIRELESS_ENTRIES_PER_PACKET,
                    report_length=WIRELESS_REPORT_LENGTH,
                )
                writes += _send_frame(device, packets)
                frames += 1
                print(f"{frames} full frames / {writes} successful reports", end="\r", flush=True)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        device.close()
    elapsed = time.monotonic() - started
    print(f"Completed: {frames} complete frames, {writes} reports in {elapsed:.1f}s; no write failures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
