import pytest

from fantech_he68.protocol import (
    KNOWN_STATIC_COLOR_TEMPLATE,
    RgbColor,
    build_set_color_packet,
    decode_battery_percentage,
)


def test_verified_color_packet_has_only_verified_fields() -> None:
    # The opaque non-RGB bytes represent a previously captured packet, not defaults.
    template = bytearray([0x6A]) * 64
    template[:3] = bytes.fromhex("AA 23 10")
    template[22:24] = bytes.fromhex("AA 55")
    template[24:] = bytes(40)
    packet = build_set_color_packet(RgbColor(255, 128, 32), bytes(template))

    assert len(packet) == 64
    assert packet[:3] == bytes.fromhex("AA 23 10")
    assert packet[3:9] == bytes([0x6A]) * 6
    assert packet[9:13] == bytes((255, 128, 32, 255))
    assert packet[13:22] == bytes([0x6A]) * 9
    assert packet[22:24] == bytes.fromhex("AA 55")
    assert packet[24:] == b"\0" * 40


def test_default_packet_is_based_on_the_supplied_capture() -> None:
    packet = build_set_color_packet(RgbColor(0, 255, 0))

    assert len(KNOWN_STATIC_COLOR_TEMPLATE) == 64
    assert packet[3:9] == KNOWN_STATIC_COLOR_TEMPLATE[3:9]
    assert packet[9:13] == bytes((0, 255, 0, 255))
    assert packet[13:22] == KNOWN_STATIC_COLOR_TEMPLATE[13:22]


def test_decode_captured_wireless_battery_response() -> None:
    response = bytes.fromhex(
        "55 10 18 00 00 00 00 00 00 00 00 92 45 0C CB 80 "
        "15 01 00 00 05 00 02 00 02 64 00 00 05 00 00 00"
    )

    assert decode_battery_percentage(response) == 92


def test_rejects_invalid_wireless_battery_response() -> None:
    with pytest.raises(ValueError, match="invalid BCD percentage"):
        decode_battery_percentage(bytes.fromhex("55 10 18") + b"\0" * 8 + bytes((0xFA,)) + b"\0" * 20)
