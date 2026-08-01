from pathlib import Path

from fantech_he68.packetdb import compare_packets, decode_packet, load_byte_database, load_packet


def test_static_red_capture_is_loadable_and_decodable() -> None:
    root = Path(__file__).resolve().parents[1]
    packet = load_packet(root / "captures" / "lighting" / "static_red")
    decoded = decode_packet(packet, load_byte_database(root / "database" / "bytes.json"))

    assert decoded["header"] == "AA"
    assert decoded["command"] == "23"
    assert decoded["subcommand"] == "10"
    assert decoded["fields"][9]["name"] == "Red"


def test_packet_diff_only_reports_changed_verified_rgb_byte() -> None:
    root = Path(__file__).resolve().parents[1]
    baseline = load_packet(root / "captures" / "lighting" / "static_red")
    green = bytearray(baseline)
    green[9:12] = bytes((0, 255, 0))
    differences = compare_packets(baseline, bytes(green), load_byte_database(root / "database" / "bytes.json"))

    assert [(item.offset, item.name, item.confidence) for item in differences] == [
        (9, "Red", "Verified"),
        (10, "Green", "Verified"),
    ]
