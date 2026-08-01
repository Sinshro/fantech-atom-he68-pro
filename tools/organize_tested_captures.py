"""Split replay-tested WebHID batches into immutable capture folders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fantech_he68.capture import CaptureSession
from fantech_he68.collection import create_capture_folder
from replay_sequence import load_outbound_packets

STANDARD_NAMES = (
    "static_bright", "single_point_on", "single_point_off", "starry_sky", "snowfall",
    "floral_competition", "dynamic_breathing", "spectrum_cycle", "color_fountain",
    "lighting_effect_10", "lighting_effect_11", "turning_peaks", "one_touch_to_fire",
    "lighting_effect_14", "ripples_spread", "endless_flow", "lighting_effect_17",
    "lighting_effect_18", "back_and_forth",
)
CUSTOM_PACKETS_PER_UPDATE = 10
PERFORMANCE_PACKETS_PER_UPDATE = 19


def mark_verified(folder: Path, *, source: Path, packet_range: str) -> None:
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({
        "verified": True,
        "verification": "Replayed successfully through native HID transport with device responses observed.",
        "source_recording": str(source),
        "source_packet_range": packet_range,
    })
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    with (folder / "notes.md").open("a", encoding="utf-8") as notes:
        notes.write("\n## Replay test\nVerified by successful native HID replay on 2026-07-31.\n")


def make_session(label: str, packets: list[bytes]) -> CaptureSession:
    session = CaptureSession(label)
    for packet in packets:
        session.record_outbound(packet)
    return session


def save_if_missing(*, root: Path, name: str, feature: str, session: CaptureSession, source: Path, packet_range: str) -> bool:
    destination = root / "lighting" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    folder, _ = create_capture_folder(
        session, root=root, category="lighting", feature=feature, capture_name=name,
        action=f"Observed UI action from {source.name}; source packets {packet_range}.",
    )
    mark_verified(folder, source=source, packet_range=packet_range)
    print(f"Created {folder}")
    return True


def save_performance_capture(*, root: Path, source: Path) -> bool:
    packets = load_outbound_packets(source)
    if len(packets) != PERFORMANCE_PACKETS_PER_UPDATE * 4:
        raise ValueError(
            f"expected four {PERFORMANCE_PACKETS_PER_UPDATE}-packet Performance updates, got {len(packets)} packets"
        )
    name = "wasd_trigger_distance_2mm"
    destination = root / "performance" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    final_start = PERFORMANCE_PACKETS_PER_UPDATE * 3
    folder, _ = create_capture_folder(
        make_session(name, packets[final_start:]),
        root=root,
        category="performance",
        feature="WASD trigger distance 2.00 mm",
        capture_name=name,
        action="WASD selected in the official software; trigger-distance slider set to 2.00 mm.",
    )
    mark_verified(folder, source=source, packet_range="58-76")
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification"] = "User confirmed the replayed WASD configuration requires a deeper press than Q."
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Created {folder}")
    return True


def save_fast_trigger_capture(*, root: Path, source: Path) -> bool:
    packets = load_outbound_packets(source)
    if len(packets) != PERFORMANCE_PACKETS_PER_UPDATE * 4:
        raise ValueError(
            f"expected four {PERFORMANCE_PACKETS_PER_UPDATE}-packet Fast Trigger updates, got {len(packets)} packets"
        )
    name = "wasd_fast_trigger_on"
    destination = root / "performance" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    final_start = PERFORMANCE_PACKETS_PER_UPDATE * 3
    folder, _ = create_capture_folder(
        make_session(name, packets[final_start:]),
        root=root,
        category="performance",
        feature="WASD Fast Trigger on",
        capture_name=name,
        action="WASD selected in the official software; Fast Trigger toggled on.",
    )
    mark_verified(folder, source=source, packet_range="58-76")
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification"] = "User confirmed the replayed state shows Fast Trigger enabled with WASD selected."
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Created {folder}")
    return True


def save_office_mode_capture(*, root: Path, source: Path) -> bool:
    return save_verified_preset_capture(root=root, source=source, name="office_mode", feature="Office Mode")


def save_verified_preset_capture(*, root: Path, source: Path, name: str, feature: str) -> bool:
    packets = load_outbound_packets(source)
    if len(packets) != PERFORMANCE_PACKETS_PER_UPDATE:
        raise ValueError(
            f"expected one {PERFORMANCE_PACKETS_PER_UPDATE}-packet Office Mode update, got {len(packets)} packets"
        )
    destination = root / "performance" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    folder, _ = create_capture_folder(
        make_session(name, packets),
        root=root,
        category="performance",
        feature=feature,
        capture_name=name,
        action=f"{feature} selected in the official software.",
    )
    mark_verified(folder, source=source, packet_range="1-19")
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification"] = f"User confirmed {feature} replay works on the keyboard."
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Created {folder}")
    return True


def save_dead_zone_capture(*, root: Path, source: Path) -> bool:
    packets = load_outbound_packets(source)
    if len(packets) != 3:
        raise ValueError(f"expected three cumulative Dead Zone commands, got {len(packets)} packets")
    name = "wasd_dead_zone_top_bottom_0_5mm"
    destination = root / "performance" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    folder, _ = create_capture_folder(
        make_session(name, packets),
        root=root,
        category="performance",
        feature="WASD Dead Zone Top and Bottom 0.5 mm",
        capture_name=name,
        action="WASD selected; Dead Zone enabled; Top and Bottom Dead Zone set to 0.5 mm.",
    )
    mark_verified(folder, source=source, packet_range="1-3")
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification"] = "User confirmed replay works on the keyboard."
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Created {folder}")
    return True


def save_custom_key_capture(*, root: Path, source: Path) -> bool:
    packets = load_outbound_packets(source)
    if len(packets) != 10:
        raise ValueError(f"expected one 10-packet Custom Keys update, got {len(packets)} packets")
    name = "q_to_a"
    destination = root / "custom_keys" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    folder, _ = create_capture_folder(
        make_session(name, packets),
        root=root,
        category="custom_keys",
        feature="Q to A",
        capture_name=name,
        action="Q selected in Custom Keys; remapped to A.",
    )
    mark_verified(folder, source=source, packet_range="1-10")
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification"] = "User confirmed physical Q types A after replay."
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Created {folder}")
    return True


def save_stability_capture(*, root: Path, source: Path, enabled: bool) -> bool:
    packets = load_outbound_packets(source)
    expected_count = 1 if enabled else 2
    if len(packets) != expected_count:
        raise ValueError(f"expected {expected_count} Stability Mode command(s), got {len(packets)} packets")
    state = "on" if enabled else "off"
    name = f"stability_mode_{state}"
    destination = root / "settings" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    folder, _ = create_capture_folder(
        make_session(name, packets), root=root, category="settings",
        feature=f"Stability Mode {state}", capture_name=name,
        action=f"Stability Mode toggled {state} in the official software.",
    )
    mark_verified(folder, source=source, packet_range=f"1-{len(packets)}")
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification"] = f"User confirmed Stability Mode {state} replay works on the keyboard."
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Created {folder}")
    return True


def save_adaptive_calibration_capture(*, root: Path, source: Path, enabled: bool) -> bool:
    packets = load_outbound_packets(source)
    expected_count = 2 if enabled else 1
    if len(packets) != expected_count:
        raise ValueError(f"expected {expected_count} Adaptive Calibration command(s), got {len(packets)} packets")
    state = "on" if enabled else "off"
    name = f"adaptive_dynamic_calibration_{state}"
    destination = root / "settings" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    folder, _ = create_capture_folder(
        make_session(name, packets), root=root, category="settings",
        feature=f"Adaptive Dynamic Calibration {state}", capture_name=name,
        action=f"Adaptive Dynamic Calibration toggled {state} in the official software.",
    )
    mark_verified(folder, source=source, packet_range=f"1-{len(packets)}")
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification"] = f"User confirmed Adaptive Dynamic Calibration {state} replay works on the keyboard."
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Created {folder}")
    return True


def save_return_rate_capture(*, root: Path, source: Path, rate: str) -> bool:
    packets = load_outbound_packets(source)
    if len(packets) != 1:
        raise ValueError(f"expected one {rate.upper()} Return Rate command, got {len(packets)} packets")
    name = f"return_rate_{rate}"
    destination = root / "settings" / name
    if destination.exists():
        print(f"Keeping existing capture: {destination}")
        return False
    folder, _ = create_capture_folder(
        make_session(name, packets), root=root, category="settings",
        feature=f"{rate.upper()} Return Rate", capture_name=name,
        action=f"{rate.upper()} Return Rate selected in the official software.",
    )
    mark_verified(folder, source=source, packet_range="1")
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["verification"] = f"User confirmed {rate.upper()} Return Rate replay works after the expected USB reconnection."
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Created {folder}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize replay-tested lighting, Custom, and Performance batches.")
    parser.add_argument("--root", type=Path, default=Path("captures"))
    parser.add_argument("--standard", type=Path, default=Path("lighting/capture.json"))
    parser.add_argument("--custom", type=Path, default=Path("lighting/capture (1).json"))
    parser.add_argument("--performance", type=Path, default=Path("lighting/capture (4).json"))
    parser.add_argument("--fast-trigger", type=Path, default=Path("lighting/fasst triggeer.json"))
    parser.add_argument("--office-mode", type=Path, default=Path("lighting/capture (5).json"))
    parser.add_argument("--beginner-mode", type=Path, default=Path("lighting/beginner.json"))
    parser.add_argument("--game-mode", type=Path, default=Path("lighting/gaamer].json"))
    parser.add_argument("--dead-zone", type=Path, default=Path("lighting/bottom dead zone 0.5.json"))
    parser.add_argument("--custom-q-to-a", type=Path, default=Path("lighting/capture (7).json"))
    parser.add_argument("--stability-on", type=Path, default=Path("lighting/stablity mode on.json"))
    parser.add_argument("--stability-off", type=Path, default=Path("lighting/stablity mode off.json"))
    parser.add_argument("--adaptive-on", type=Path, default=Path("lighting/on.json"))
    parser.add_argument("--adaptive-off", type=Path, default=Path("lighting/off.json"))
    parser.add_argument("--return-rate-1k", type=Path, default=Path("lighting/1k.json"))
    parser.add_argument("--return-rate-4k", type=Path, default=Path("lighting/4k.json"))
    parser.add_argument("--return-rate-8k", type=Path, default=Path("lighting/8k.json"))
    args = parser.parse_args()

    standard = load_outbound_packets(args.standard)
    if len(standard) != len(STANDARD_NAMES):
        parser.error(f"expected {len(STANDARD_NAMES)} standard-effect packets, got {len(standard)}")
    for index, (name, packet) in enumerate(zip(STANDARD_NAMES, standard, strict=True), 1):
        save_if_missing(root=args.root, name=name, feature=name.replace("_", " "), session=make_session(name, [packet]),
                        source=args.standard, packet_range=str(index))

    custom = load_outbound_packets(args.custom)
    if len(custom) % CUSTOM_PACKETS_PER_UPDATE:
        parser.error(f"Custom recording has {len(custom)} packets; expected groups of {CUSTOM_PACKETS_PER_UPDATE}")
    for group, start in enumerate(range(0, len(custom), CUSTOM_PACKETS_PER_UPDATE), 1):
        name = f"custom_state_{group:02}"
        save_if_missing(root=args.root, name=name, feature=f"Custom state {group}",
                        session=make_session(name, custom[start : start + CUSTOM_PACKETS_PER_UPDATE]),
                        source=args.custom, packet_range=f"{start + 1}-{start + CUSTOM_PACKETS_PER_UPDATE}")
    try:
        save_performance_capture(root=args.root, source=args.performance)
        save_fast_trigger_capture(root=args.root, source=args.fast_trigger)
        save_office_mode_capture(root=args.root, source=args.office_mode)
        save_verified_preset_capture(root=args.root, source=args.beginner_mode, name="beginner_mode", feature="Beginner Mode")
        save_verified_preset_capture(root=args.root, source=args.game_mode, name="game_mode", feature="Game Mode")
        save_dead_zone_capture(root=args.root, source=args.dead_zone)
        save_custom_key_capture(root=args.root, source=args.custom_q_to_a)
        save_stability_capture(root=args.root, source=args.stability_on, enabled=True)
        save_stability_capture(root=args.root, source=args.stability_off, enabled=False)
        save_adaptive_calibration_capture(root=args.root, source=args.adaptive_on, enabled=True)
        save_adaptive_calibration_capture(root=args.root, source=args.adaptive_off, enabled=False)
        save_return_rate_capture(root=args.root, source=args.return_rate_1k, rate="1k")
        save_return_rate_capture(root=args.root, source=args.return_rate_4k, rate="4k")
        save_return_rate_capture(root=args.root, source=args.return_rate_8k, rate="8k")
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
