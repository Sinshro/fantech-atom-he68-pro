import importlib.util
import os
import time
from pathlib import Path


def load_wizard() -> object:
    source = Path(__file__).resolve().parents[1] / "tools" / "capture_wizard.py"
    spec = importlib.util.spec_from_file_location("capture_wizard", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_newest_recording_ignores_old_downloads(tmp_path: Path, monkeypatch: object) -> None:
    wizard = load_wizard()
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    old = downloads / "old.json"
    old.write_text("{}")
    os.utime(old, (1, 1))
    fresh = downloads / "fresh.json"
    fresh.write_text("{}")
    monkeypatch.setattr(wizard.Path, "home", lambda: tmp_path)
    assert wizard.newest_web_recording(modified_after=time.time() - 2) == fresh
