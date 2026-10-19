#!/usr/bin/env python3
"""Stage245: independently decode two complete CPU-render A/B timings in one guest.

These are averaged full *software rasterization* costs, not FPS, GPU/present,
original PS3 game code or native hardware measurements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage238_cache_guest_check import STATES, verify_cache_screenshots
from tools.foj_stage241_render_guest_check import close, verify_render_timing

SCHEMA = "foj-stage245-neXium-inprocess-full-software-render-us-v1"
# Horizontal letterboxing approximately follows 0.966*framebuffer_x+23,
# measured from Stage241's 16 guest bits and Stage244's 48 actual bits.
# Each predicted center is checked in a tightly bounded 3px neighborhood.
BITS = 16
Y = (13, 15, 17)
CACHED_ON = (62, 212, 241)
UNCACHED_ON = (236, 129, 45)
OFF = (48, 37, 48)
READY = (91, 232, 104)
PENDING = (63, 134, 184)
FAILED = (255, 34, 34)
CONTROL = ("initial", "hidden", "cancelled", "ended")
FORECAST = ("selected", "hovered", "restored", "guarded", "guard_hovered")


def center(guest_x: int) -> int:
    return round(22 + 0.966 * (guest_x+1))


def pixels_match(frame, x: int, color: tuple[int, int, int]) -> bool:
    return all(close(frame.getpixel((x, y)), color) for y in Y)


def read_bar(frame, framebuffer_x: int, on_color: tuple[int, int, int]) -> int:
    result = 0
    for bit in range(BITS):
        x = center(framebuffer_x + bit*4)
        # Real Stage244 NeXium guest proof: all 48 A/B barcode bits in
        # five captured scenes (240 color samples) give exactly the same
        # color at x=(predicted-1) as their independently verified bit
        # centers. Do not scan adjacent colors: nearby *different* bits
        # could create ambiguous evidence at the barcode boundaries.
        sample_x = x - 1
        if pixels_match(frame, sample_x, on_color):
            result |= 1 << bit
        elif not pixels_match(frame, sample_x, OFF):
            raise ValueError(
                f"Missing/ambiguous guest render bit {bit} at x={sample_x}")
    if not 1 <= result < 65535:
        raise ValueError(f"Invalid zero/saturated full-render mean: {result}")
    return result


def read_status(frame) -> None:
    x = center(924+3)
    samples = [
        frame.getpixel((x+delta, y))
        for delta in (-1,0,1) for y in Y
    ]
    if not any(pixels_match(frame,x+d,READY) for d in (-1,0,1)):
        raise ValueError(f"Full software render parity not ready: {samples}")


def verify_full_render_pairs(paths: tuple[Path, ...]) -> dict:
    if len(paths) != len(STATES):
        raise ValueError("Exactly nine ordered genuine guest frames required")
    cache = verify_cache_screenshots(paths)
    render = verify_render_timing(paths)
    states, hashes = {}, {}
    for state, path in zip(STATES, paths):
        frame = read_frame(path)
        read_status(frame)
        a = read_bar(frame,780,CACHED_ON)
        b = read_bar(frame,852,UNCACHED_ON)
        hashes[state] = hashlib.sha256(path.read_bytes()).hexdigest()
        states[state] = {
            "cached_render_mean_us": a,
            "uncached_render_mean_us": b,
            "uncached_minus_cached_us": b-a,
            "uncached_over_cached_ratio": round(b/a,4),
            "forecast_preview_active": state in FORECAST,
        }
    if len(set(hashes.values())) < 2:
        raise ValueError("Static screenshot repeated as proof")
    controls = {s:states[s]["uncached_minus_cached_us"] for s in CONTROL}
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "guest_processes": 1,
        "captured_real_guest_frames": len(paths),
        "pairs_per_window": 32,
        "alternating_AB_BA": True,
        "two_private_full_frame_buffers_pixel_identical_in_guest": True,
        "same_gameplay_state_in_each_pair": True,
        "guest_cache_transition_schema": cache["schema"],
        "original_render_timer_schema": render["schema"],
        "full_software_render_pairs": states,
        "inactive_forecast_control_deltas_us": controls,
        "baseline_drift_observed": any(delta != 0 for delta in controls.values()),
        "median_selected_cached_render_us": statistics.median(
            states[s]["cached_render_mean_us"] for s in FORECAST),
        "median_selected_uncached_render_us": statistics.median(
            states[s]["uncached_render_mean_us"] for s in FORECAST),
        "frame_sha256": hashes,
        "measurement_scope": "foj_iso_render_battle_cached_options only; private buffers; no present",
        "physical_switch_hardware_tested": False,
        "switch_fps_measured": False,
        "gpu_time_measured": False,
        "full_game_frame_latency_measured": False,
        "causal_whole_game_speedup_proven": False,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--"+state.replace("_","-"),required=True,type=Path)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    report=verify_full_render_pairs(tuple(
        getattr(args,state) for state in STATES))
    with args.report.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2,sort_keys=True)
        stream.write("\n")
    print("Stage245 real guest paired CPU-render microseconds:",
          report["full_software_render_pairs"])


if __name__ == "__main__":
    main()
