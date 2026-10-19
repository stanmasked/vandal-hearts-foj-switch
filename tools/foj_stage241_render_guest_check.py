#!/usr/bin/env python3
"""Stage241: decode 16-bit render microseconds from nine *actual* NeXium frames.

This reports the NRO's averaged AArch64 guest-clock software-render duration.
It does not report NeXium host wall time, complete frame time, GPU time or FPS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage238_cache_guest_check import STATES, verify_cache_screenshots

SCHEMA = "foj-stage241-nexium-guest-software-render-us-v1"
# Verified from genuine 1280x720 NeXium GUI screenshots in Stage240's
# successful Stage238 run 39183860145: 16 guest framebuffer bar centers
# (starting at framebuffer x432) are slightly scaled/offset by the GUI.
BIT_X = (440, 444, 448, 452, 456, 460, 464, 467,
         471, 475, 479, 483, 487, 491, 495, 499)
SAMPLE_Y = (13, 15, 17)
# libnx RGBA8888 uint32 pixel values are little-endian in guest framebuffer:
# 0xff7fe8ff -> RGB (255,232,127) in the captured GUI frame.
ON = (255, 232, 127)
OFF = (48, 37, 48)
PENDING = (63, 134, 184)


def close(rgb: tuple[int, int, int], color: tuple[int, int, int]) -> bool:
    return all(abs(rgb[i] - color[i]) <= 8 for i in range(3))


def decode_microseconds(frame_path: Path) -> int:
    frame = read_frame(frame_path)
    result = 0
    for bit, x in enumerate(BIT_X):
        pixels = [frame.getpixel((x, y)) for y in SAMPLE_Y]
        if all(close(pixel, ON) for pixel in pixels):
            result |= 1 << bit
        elif all(close(pixel, OFF) for pixel in pixels):
            continue
        elif any(close(pixel, PENDING) for pixel in pixels):
            raise ValueError(f"{frame_path.name}: timing not yet initialized")
        else:
            raise ValueError(
                f"{frame_path.name}: missing/ambiguous timing bit {bit}: {pixels}")
    if result == 0:
        raise ValueError(f"{frame_path.name}: zero timing is not evidence")
    if result == 65535:
        raise ValueError(f"{frame_path.name}: saturated timer gives no exact cost")
    return result


def verify_render_timing(paths: tuple[Path, ...]) -> dict:
    if len(paths) != len(STATES):
        raise ValueError("Expected nine ordered real guest captures")
    # Stage238's independent cache states must still match the same nine
    # images: a static fake timing-HUD image is not game-play evidence.
    cache_receipt = verify_cache_screenshots(paths)
    values = [decode_microseconds(path) for path in paths]
    if len(set(values)) < 2:
        raise ValueError("Timer did not change across distinct guest scenes")
    checksums = {
        state: hashlib.sha256(path.read_bytes()).hexdigest()
        for state, path in zip(STATES, paths)
    }
    if len(set(checksums.values())) < 2:
        raise ValueError("Repeated same screenshot is not timing evidence")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "actual_guest_screenshots": len(paths),
        "timing_metric": "32-frame averaged software-render duration",
        "unit": "microseconds",
        "clock": "libnx armGetSystemTick + armTicksToNs",
        "measurement_scope": "foj_iso_render_battle_cached_options only",
        "render_us_by_game_state": dict(zip(STATES, values)),
        "min_render_us": min(values),
        "median_render_us": statistics.median(values),
        "max_render_us": max(values),
        "guest_timer_valid_nonzero_unsaturated": True,
        "cache_guest_proof": cache_receipt["schema"],
        "cache_transition_sequence_valid": True,
        "frame_sha256": checksums,
        "guest_frame_latency_measured": False,
        "host_wall_time_measured": False,
        "physical_switch_hardware_tested": False,
        "switch_fps_measured": False,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--" + state.replace("_", "-"),
                            required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    result = verify_render_timing(tuple(
        getattr(args, state) for state in STATES))
    with args.report.open("x", encoding="utf-8") as out:
        json.dump(result, out, sort_keys=True, indent=2)
        out.write("\n")
    print("Stage241 NeXium software-render measurement (us):",
          result["render_us_by_game_state"])


if __name__ == "__main__":
    main()
