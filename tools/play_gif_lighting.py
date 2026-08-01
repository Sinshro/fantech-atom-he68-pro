"""Play an animated GIF as a low-resolution Custom-lighting animation.

Each keyboard key is one pixel.  This keeps the device in Custom lighting and
streams ten observed-format HID reports per displayed GIF frame.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from fantech_he68.custom_lighting import KEYBOARD_ROWS, blank_table, build_custom_frame
from fantech_he68.device import AtomHE68Pro


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Play a GIF through HE68 PRO Custom lighting.")
    result.add_argument("gif", type=Path, help="animated GIF to downsample to the keyboard")
    result.add_argument("--fps", type=float, default=4.0, help="animation speed (default: 4; max: 6)")
    result.add_argument("--loops", type=int, default=0, help="number of loops; 0 means play until Ctrl+C")
    result.add_argument("--path", help="manual HIDAPI path")
    result.add_argument("--preview", type=Path, help="write a scaled keyboard-grid GIF preview, without using HID")
    result.add_argument("--no-select-custom", action="store_true", help="do not select Custom mode before playback")
    result.add_argument("--mode-recording", type=Path, default=Path("lighting/capture.json"), help="captured lighting-mode batch")
    result.add_argument("--mode-index", type=int, default=19, help="1-based Custom-mode packet in the batch")
    return result


def _import_image() -> object:
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("GIF playback needs Pillow. Install it with: py -m pip install Pillow") from error
    return Image


def load_frames(gif_path: Path) -> tuple[list[list[tuple[int, int, int]]], object]:
    """Convert GIF frames to 68 key colours and retain a grid preview image."""
    Image = _import_image()
    if not gif_path.is_file():
        raise FileNotFoundError(f"GIF not found: {gif_path}")
    image = Image.open(gif_path)
    frame_count = getattr(image, "n_frames", 1)
    frames: list[list[tuple[int, int, int]]] = []
    preview_frames: list[object] = []
    row_width = max(map(len, KEYBOARD_ROWS))
    height = len(KEYBOARD_ROWS)
    for index in range(frame_count):
        image.seek(index)
        # GIF frames can be partial; convert() asks Pillow for the composed frame.
        small = image.convert("RGB").resize((row_width, height), Image.Resampling.BOX)
        pixels = list(small.get_flattened_data())
        frames.append([(int(red), int(green), int(blue)) for red, green, blue in pixels])
        preview_frames.append(small.resize((row_width * 42, height * 42), Image.Resampling.NEAREST))
    return frames, preview_frames


def table_for_grid(grid: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Place a 15×5 GIF grid on the provisional physical-key matrix."""
    table = blank_table()
    width = max(map(len, KEYBOARD_ROWS))
    for row_index, addresses in enumerate(KEYBOARD_ROWS):
        for column, address in enumerate(addresses):
            table[address] = grid[row_index * width + column]
    return table


def write_preview(preview_frames: list[object], destination: Path, fps: float) -> None:
    duration = round(1_000 / fps)
    destination.parent.mkdir(parents=True, exist_ok=True)
    preview_frames[0].save(destination, save_all=True, append_images=preview_frames[1:], loop=0, duration=duration)


def load_mode_packet(recording: Path, index: int) -> bytes:
    """Load the observed Custom-mode selection report without interpreting it."""
    document = json.loads(recording.read_text(encoding="utf-8"))
    packets = [
        bytes.fromhex(record["payload_hex"])
        for record in document["packets"]
        if record.get("direction") == "host_to_device"
    ]
    if not 1 <= index <= len(packets):
        raise ValueError(f"--mode-index must be within 1..{len(packets)}")
    packet = packets[index - 1]
    if len(packet) != 64:
        raise ValueError("Custom-mode packet must be a 64-byte HID report")
    return packet


def main() -> int:
    args = parser().parse_args()
    if not 0 < args.fps <= 6:
        parser.error("--fps must be greater than 0 and no more than 6")
    if args.loops < 0:
        parser.error("--loops must be 0 or a positive integer")

    grids, previews = load_frames(args.gif)
    if args.preview:
        write_preview(previews, args.preview, args.fps)
        print(f"Wrote {len(previews)}-frame key-grid preview: {args.preview}")
        return 0

    frames = [build_custom_frame(table_for_grid(grid)) for grid in grids]
    print(f"Loaded {len(frames)} GIF frames; sending 10 reports per frame at {args.fps:g} FPS.")
    keyboard = AtomHE68Pro()
    keyboard.connect(args.path)
    try:
        if not args.no_select_custom:
            print("Selecting Custom lighting mode...")
            keyboard.send_packet(load_mode_packet(args.mode_recording, args.mode_index))
        loop = 0
        frame_seconds = 1 / args.fps
        while args.loops == 0 or loop < args.loops:
            for number, packets in enumerate(frames, 1):
                started = time.monotonic()
                for packet in packets:
                    keyboard.send_observed_packet(packet)
                remaining = frame_seconds - (time.monotonic() - started)
                if remaining > 0:
                    time.sleep(remaining)
                print(f"Loop {loop + 1}, frame {number}/{len(frames)}", end="\r", flush=True)
            loop += 1
    except KeyboardInterrupt:
        print("\nStopped; Custom lighting remains on the last displayed frame.")
    finally:
        keyboard.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
