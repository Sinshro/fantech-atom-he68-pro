import importlib.util
import json
from pathlib import Path

import pytest


def load_tool() -> object:
    source = Path(__file__).resolve().parents[1] / "tools" / "replay_sequence.py"
    spec = importlib.util.spec_from_file_location("replay_sequence", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_outbound_packets_keeps_only_valid_tx(tmp_path: Path) -> None:
    tool = load_tool()
    capture = tmp_path / "capture.json"
    capture.write_text(json.dumps({"packets": [
        {"direction": "host_to_device", "payload_hex": bytes(64).hex()},
        {"direction": "device_to_host", "payload_hex": bytes(64).hex()},
    ]}))
    assert tool.load_outbound_packets(capture) == [bytes(64)]


def test_load_outbound_packets_rejects_wrong_length(tmp_path: Path) -> None:
    tool = load_tool()
    capture = tmp_path / "capture.json"
    capture.write_text(json.dumps({"packets": [{"direction": "host_to_device", "payload_hex": "AA"}]}))
    with pytest.raises(ValueError, match="unexpected length"):
        tool.load_outbound_packets(capture)
