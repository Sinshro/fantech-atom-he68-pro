from fantech_he68.custom_lighting import (
    KEYBOARD_ROWS,
    TABLE_SIZE,
    WIRELESS_ENTRIES_PER_PACKET,
    WIRELESS_REPORT_LENGTH,
    build_custom_frame,
)


def test_keyboard_rows_use_official_sparse_right_side_addresses() -> None:
    assert KEYBOARD_ROWS[0] == (0, *range(17, 29), 92, 103)
    assert KEYBOARD_ROWS[3][-2:] == (90, 108)
    assert KEYBOARD_ROWS[4][-4:] == (87, 88, 89, 91)


def test_custom_frame_matches_observed_report_structure() -> None:
    table = [(0, 0, 0)] * TABLE_SIZE
    table[33] = (255, 255, 255)

    packets = build_custom_frame(table)

    assert len(packets) == 10
    assert packets[0][:8] == bytes.fromhex("AA 24 38 00 00 00 00 00")
    assert packets[2][8:12] == bytes((28, 0, 0, 0))
    assert packets[2][28:32] == bytes((33, 255, 255, 255))
    assert packets[-1][:8] == bytes.fromhex("AA 24 08 F8 01 00 01 00")
    assert packets[-1][8:16] == bytes.fromhex("7E 00 00 00 7F 00 00 00")


def test_wireless_custom_frame_matches_observed_32_byte_structure() -> None:
    table = [(0, 0, 0)] * TABLE_SIZE
    table[33] = (255, 13, 0)

    packets = build_custom_frame(
        table,
        entries_per_packet=WIRELESS_ENTRIES_PER_PACKET,
        report_length=WIRELESS_REPORT_LENGTH,
    )

    assert len(packets) == 22
    assert packets[0] == bytes.fromhex(
        "AA 24 18 00 00 00 00 00 00 00 00 00 01 00 00 00 "
        "02 00 00 00 03 00 00 00 04 00 00 00 05 00 00 00"
    )
    assert packets[5] == bytes.fromhex(
        "AA 24 18 78 00 00 00 00 1E 00 00 00 1F 00 00 00 "
        "20 00 00 00 21 FF 0D 00 22 00 00 00 23 00 00 00"
    )
    assert packets[-1] == bytes.fromhex(
        "AA 24 08 F8 01 00 01 00 7E 00 00 00 7F 00 00 00 " + "00 " * 16
    )
