import pytest

from fantech_he68.capture import CaptureSession
from fantech_he68.device import AtomHE68Pro, DeviceNotFoundError, HidProtocolError


def captured_color_template() -> bytes:
    """A structurally valid opaque packet capture fixture."""
    template = bytearray(64)
    template[:3] = bytes.fromhex("AA 23 10")
    template[22:24] = bytes.fromhex("AA 55")
    return bytes(template)


class FakeDevice:
    def __init__(self, response: list[int]) -> None:
        self.response = response
        self.opened_path: bytes | None = None
        self.writes: list[bytes] = []
        self.closed = False

    def open_path(self, path: bytes) -> None:
        self.opened_path = path

    def close(self) -> None:
        self.closed = True

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def read(self, max_length: int, timeout_ms: int = 0) -> list[int]:
        return self.response


class FakeHid:
    def __init__(self, entries: list[dict[str, object]], response: list[int]) -> None:
        self.entries = entries
        self.device_instance = FakeDevice(response)

    def enumerate(self, vendor_id: int, product_id: int) -> list[dict[str, object]]:
        assert (vendor_id, product_id) == (0x0C45, 0x80CB)
        return self.entries

    def device(self) -> FakeDevice:
        return self.device_instance


def test_set_color_writes_report_id_then_verified_64_byte_payload_and_accepts_ack() -> None:
    hid = FakeHid([{"usage_page": 0xFF68, "path": b"vendor-interface"}], [0, 0x55, 0x23, 0x10] + [0] * 61)
    keyboard = AtomHE68Pro(hid_module=hid, color_packet_template=captured_color_template())

    keyboard.connect()
    ack = keyboard.set_color(255, 128, 32)

    assert ack[:3] == bytes.fromhex("55 23 10")
    assert hid.device_instance.writes == [bytes((0,)) + bytes.fromhex("AA 23 10 00 00 00 00 00 00 FF 80 20 FF") + b"\0" * 9 + bytes.fromhex("AA 55") + b"\0" * 40]


def test_rejects_non_ack_response() -> None:
    hid = FakeHid([{"usage_page": 0xFF68, "path": b"vendor-interface"}], [0xAA, 0x23, 0x10])
    keyboard = AtomHE68Pro(hid_module=hid, color_packet_template=captured_color_template())
    keyboard.connect()

    with pytest.raises(HidProtocolError, match="expected 55 23 10"):
        keyboard.set_color(1, 2, 3)


def test_requires_vendor_usage_page() -> None:
    hid = FakeHid([{"usage_page": 0x0001, "path": b"keyboard-interface"}], [])

    with pytest.raises(DeviceNotFoundError, match="0xFF68"):
        AtomHE68Pro(hid_module=hid).connect()


def test_manual_path_bypasses_automatic_selection_without_claiming_a_match() -> None:
    hid = FakeHid([], [])
    keyboard = AtomHE68Pro(hid_module=hid)

    keyboard.connect("manual-hid-path")

    assert hid.device_instance.opened_path == b"manual-hid-path"


def test_capture_session_records_and_pairs_verified_request_and_ack(tmp_path) -> None:
    hid = FakeHid(
        [{"usage_page": 0xFF68, "path": b"vendor-interface"}],
        [0, 0x55, 0x23, 0x10] + [0] * 61,
    )
    session = CaptureSession("test")
    keyboard = AtomHE68Pro(
        hid_module=hid,
        color_packet_template=captured_color_template(),
        capture_session=session,
    )
    keyboard.connect()
    keyboard.set_color(1, 2, 3)

    request, acknowledgement = session.packets
    assert request.direction == "host_to_device"
    assert acknowledgement.direction == "device_to_host"
    assert request.paired_sequence == acknowledgement.sequence
    assert acknowledgement.paired_sequence == request.sequence
    paths = session.save(tmp_path)
    assert paths.json_path.exists()
    assert paths.binary_path.exists()
    assert paths.binary_path.read_bytes().startswith(b"H68C")
