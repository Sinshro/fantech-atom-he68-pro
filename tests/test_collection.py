from pathlib import Path

from fantech_he68.capture import CaptureSession
from fantech_he68.collection import create_capture_folder, validate_session


def test_capture_folder_is_complete_and_loadable(tmp_path: Path) -> None:
    session = CaptureSession("test")
    session.record_outbound(bytes(64))
    session.record_inbound(bytes.fromhex("55 23 10") + bytes(61))

    destination, validation = create_capture_folder(
        session, root=tmp_path, category="lighting", feature="Dynamic Breathing", capture_name="dynamic breathing"
    )

    assert validation.has_single_request_ack_pair
    assert (destination / "session.json").exists()
    assert (destination / "session.bin").exists()
    assert (destination / "metadata.json").exists()
    assert "Dynamic Breathing" in (destination / "notes.md").read_text()


def test_validation_warns_when_ack_is_missing() -> None:
    session = CaptureSession()
    session.record_outbound(bytes(64))
    assert "No ACK observed." in validate_session(session).warnings
