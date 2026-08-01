"""Custom-lighting frame construction for the Atom HE68 PRO.

The official configurator writes one complete 128-entry RGB table per Custom
lighting update.  Entries are sent in ten 64-byte reports: nine reports with
14 entries and a final, committing report with two entries.

Only the Q/W/E/R/T/Y addresses have been confirmed from a capture.  The
remaining addresses in :data:`KEYBOARD_ROWS` follow the same 16-column matrix
layout and should be treated as a provisional physical-layout map until tested
on the keyboard.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .protocol import REPORT_LENGTH

RGB = tuple[int, int, int]
TABLE_SIZE = 128
WIRED_ENTRIES_PER_PACKET = 14
WIRED_REPORT_LENGTH = 64
WIRELESS_ENTRIES_PER_PACKET = 6
WIRELESS_REPORT_LENGTH = 32

# This is the 68-key ANSI layout and RGB-table address list displayed by the
# official HE68 software.  The right-side and wide-key addresses are sparse.
KEYBOARD_ROWS: tuple[tuple[int, ...], ...] = (
    (0, *range(17, 29), 92, 103),
    (*range(32, 45), 60, 106),
    (*range(48, 60), 76, 105),
    (*range(64, 76), 90, 108),
    (*range(80, 86), 87, 88, 89, 91),
)


def _validate_rgb(color: Sequence[int]) -> RGB:
    if len(color) != 3 or any(not 0 <= component <= 255 for component in color):
        raise ValueError("each RGB colour must contain three values from 0 through 255")
    return (int(color[0]), int(color[1]), int(color[2]))


def build_custom_frame(
    colors: Iterable[Sequence[int]],
    *,
    entries_per_packet: int = WIRED_ENTRIES_PER_PACKET,
    report_length: int = WIRED_REPORT_LENGTH,
) -> list[bytes]:
    """Build a capture-backed Custom-lighting update for 128 RGB slots.

    ``colors`` must provide one RGB value for each table address, from 0 to 127.
    The function deliberately does not make claims about which physical key an
    unverified address represents. Wired keyboards use 14 entries in 64-byte
    reports; the 2.4 GHz dongle uses 6 entries in 32-byte reports.
    """
    table = [_validate_rgb(color) for color in colors]
    if len(table) != TABLE_SIZE:
        raise ValueError(f"expected {TABLE_SIZE} RGB entries, got {len(table)}")
    if entries_per_packet <= 0 or entries_per_packet * 4 + 8 > report_length:
        raise ValueError("entry count does not fit the requested report length")

    packets: list[bytes] = []
    for start in range(0, TABLE_SIZE, entries_per_packet):
        count = min(entries_per_packet, TABLE_SIZE - start)
        payload = bytearray(report_length)
        payload[0:2] = b"\xAA\x24"
        payload[2] = count * 4
        # Captures encode this as the byte offset into the 4-byte RGB table,
        # rather than as an entry number (0, 56, 112, ... 504).
        payload[3:6] = (start * 4).to_bytes(3, "little")
        # The official final report sets this flag, committing the full table.
        payload[6] = 1 if start + count == TABLE_SIZE else 0
        cursor = 8
        for address in range(start, start + count):
            red, green, blue = table[address]
            payload[cursor : cursor + 4] = bytes((address, red, green, blue))
            cursor += 4
        packets.append(bytes(payload))
    return packets


def blank_table() -> list[RGB]:
    """Return a black 128-entry Custom-lighting table."""
    return [(0, 0, 0)] * TABLE_SIZE
