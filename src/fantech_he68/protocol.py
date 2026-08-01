"""Documented, experimentally verified portions of the HE68 PRO protocol.

Do not add values here unless a packet capture verifies them.
"""

from __future__ import annotations

from dataclasses import dataclass

REPORT_LENGTH = 64
REPORT_ID = 0
VENDOR_ID = 0x0C45
PRODUCT_ID = 0x80CB
USAGE_PAGE = 0xFF68

HOST_PREFIX = bytes((0xAA, 0x23, 0x10))
ACK_PREFIX = bytes((0x55, 0x23, 0x10))
TERMINATOR = bytes((0xAA, 0x55))
RGB_OFFSET = 9
ALPHA_OFFSET = 12
TERMINATOR_OFFSET = 22

# Captured from the official software. This is a complete 64-byte static-color
# command, not a synthesized packet. It provides the only known-safe baseline for
# set_color(). TODO: determine the semantics of bytes 3..8 and 13..21.
KNOWN_STATIC_COLOR_TEMPLATE = bytes.fromhex(
    "AA2310000000010001FF0000FF000000000404000000AA55"
    + "00" * 40
)


@dataclass(frozen=True, slots=True)
class RgbColor:
    """An 8-bit RGB color with the verified fixed alpha/brightness byte."""

    red: int
    green: int
    blue: int
    alpha: int = 0xFF

    def __post_init__(self) -> None:
        for name, value in (
            ("red", self.red),
            ("green", self.green),
            ("blue", self.blue),
            ("alpha", self.alpha),
        ):
            if not isinstance(value, int) or not 0 <= value <= 0xFF:
                raise ValueError(f"{name} must be an integer from 0 through 255")


def build_set_color_packet(
    color: RgbColor, captured_template: bytes = KNOWN_STATIC_COLOR_TEMPLATE
) -> bytes:
    """Build the sole currently verified color-control packet.

    TODO(bytes 3..8): Meaning unknown. Values are preserved from the capture.
    TODO(bytes 13..21): Meaning unknown. Values are preserved from the capture.
    TODO(alpha): Its position/value are verified in captures, but whether it is
    brightness, opacity, or another field has not yet been independently proven.
    """
    if len(captured_template) != REPORT_LENGTH:
        raise ValueError(f"captured_template must be exactly {REPORT_LENGTH} bytes")
    if captured_template[: len(HOST_PREFIX)] != HOST_PREFIX:
        raise ValueError("captured_template does not begin with the verified AA 23 10 prefix")
    if (
        captured_template[TERMINATOR_OFFSET : TERMINATOR_OFFSET + len(TERMINATOR)]
        != TERMINATOR
    ):
        raise ValueError("captured_template does not contain the verified AA 55 terminator")
    if any(captured_template[TERMINATOR_OFFSET + len(TERMINATOR) :]):
        raise ValueError("captured_template bytes 24..63 must be the verified zero padding")
    # Do not manufacture unknown field values. Start from an observed packet and
    # overwrite only fields whose offsets and values have been verified.
    packet = bytearray(captured_template)
    packet[:3] = HOST_PREFIX
    packet[RGB_OFFSET : ALPHA_OFFSET + 1] = bytes(
        (color.red, color.green, color.blue, color.alpha)
    )
    packet[TERMINATOR_OFFSET : TERMINATOR_OFFSET + len(TERMINATOR)] = TERMINATOR
    # Bytes 24..63 are experimentally observed zero padding.
    packet[TERMINATOR_OFFSET + len(TERMINATOR) :] = bytes(
        REPORT_LENGTH - (TERMINATOR_OFFSET + len(TERMINATOR))
    )
    return bytes(packet)


def is_ack_for(packet: bytes) -> bool:
    """Return whether *packet* begins with the experimentally observed ACK prefix."""
    return len(packet) >= len(ACK_PREFIX) and packet[: len(ACK_PREFIX)] == ACK_PREFIX
