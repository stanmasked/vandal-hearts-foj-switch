#!/usr/bin/env python3
"""Stage244: verify *same guest process* AB/BA forecast measurements.

Read independently measured 24-bit nanoseconds/call from a real generated
Switch NRO running in NeXium. The two bars are NOT frame time or FPS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage238_cache_guest_check import (
    STATES, verify_cache_screenshots,
)
from tools.foj_stage241_render_guest_check import close, verify_render_timing

SCHEMA = "foj-stage244-nexium-inprocess-paired-threat-ns-v1"
SAMPLED = ("selected", "hovered", "restored", "guarded", "guard_hovered")
INACTIVE = ("initial", "hidden", "cancelled", "ended")
# Actual Stage243 NeXium screenshots show guest x432/492 timing bars at
# GUI centers x440/499 (16 authenticated Stage241 bits). Interpolate
# the verified ~59/60 horizontal scale rather than assuming +8 pixels
# everywhere. The Stage243 x508 mode tile centers at GUI x516 too.
def gui_center(framebuffer_x: int) -> int:
    return round(440 + (framebuffer_x - 432) * 59 / 60)


CACHED_X = tuple(gui_center(528 + 4*i) for i in range(24))
UNCACHED_X = tuple(gui_center(644 + 4*i) for i in range(24))
BIT_Y = (13, 15, 17)
STATUS_X = (759, 760, 761)
ON_CACHED = (111, 170, 51)
ON_UNCACHED = (229, 111, 163)
OFF = (48, 37, 48)
PENDING = (63, 134, 184)
READY = (86, 201, 51)
FAILED = (255, 34, 34)


def decode_bits(image, xs: tuple[int, ...], on: tuple[int, int, int]) -> int:
    raw = 0
    for bit,x in enumerate(xs):
        pixels = [image.getpixel((x,y)) for y in BIT_Y]
        if all(close(p,on) for p in pixels):
            raw |= 1 << bit
        elif all(close(p,OFF) for p in pixels):
            continue
        else:
            raise ValueError(f"Guest paired timing bit {bit} is invalid/pending: {pixels}")
    if not 0 < raw < 16777215:
        raise ValueError(f"Invalid or saturated nanosecond result {raw}")
    return raw


def validate_guest_pair_screenshots(paths: tuple[Path, ...]) -> dict:
    if len(paths) != len(STATES):
        raise ValueError("Nine ordered genuine guest screenshots required")
    # Gameplay input sequence and cache hits are proved independently.
    cache = verify_cache_screenshots(paths)
    render = verify_render_timing(paths)
    values = {}
    hashes = {}
    for state,path in zip(STATES, paths):
        image = read_frame(path)
        checks = [image.getpixel((x,y)) for x in STATUS_X for y in BIT_Y]
        hashes[state] = hashlib.sha256(path.read_bytes()).hexdigest()
        if state in INACTIVE:
            if not all(close(p,PENDING) for p in checks):
                raise ValueError(f"{state}: benchmark ran in inactive battle state {checks}")
            continue
        if state not in SAMPLED:
            raise ValueError(f"Unexpected battle state {state}")
        if not all(close(p,READY) for p in checks):
            raise ValueError(f"{state}: 32 AB/BA pairs incomplete or parity failed {checks}")
        cached = decode_bits(image, CACHED_X, ON_CACHED)
        uncached = decode_bits(image, UNCACHED_X, ON_UNCACHED)
        values[state] = {
            "cached_warm_ns_per_call": cached,
            "uncached_ns_per_call": uncached,
            "uncached_minus_cached_ns": uncached-cached,
            "observed_uncached_over_cached_ratio": round(uncached/cached,4),
        }
    if len(set(hashes.values())) < 2:
        raise ValueError("Identical screenshots are not game-play evidence")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "nro_research_type": "generated-only 8x6 tactical prototype",
        "independent_guest_processes": 1,
        "real_guest_screenshots": len(paths),
        "paired_conditions_per_completed_window": 32,
        "calls_per_condition_per_pair": 16,
        "AB_BA_order_alternating": True,
        "cached_path_warm_before_timing": True,
        "gameplay_preview_parity_verified_inside_guest": True,
        "original_battle_and_cache_guest_proof": cache["schema"],
        "original_render_guest_proof": render["schema"],
        "guest_scene_values_ns": values,
        "median_warm_cached_ns": statistics.median(
            row["cached_warm_ns_per_call"] for row in values.values()),
        "median_uncached_ns": statistics.median(
            row["uncached_ns_per_call"] for row in values.values()),
        "frame_sha256": hashes,
        "measurement_scope": "threat forecast only, not whole software renderer",
        "physical_switch_hardware_tested": False,
        "switch_fps_measured": False,
        "guest_frame_latency_measured": False,
        "gpu_time_measured": False,
        "causal_game_fps_speedup_verified": False,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--" + state.replace("_","-"),required=True,type=Path)
    parser.add_argument("--report",required=True,type=Path)
    args=parser.parse_args()
    report=validate_guest_pair_screenshots(tuple(
        getattr(args,state) for state in STATES))
    with args.report.open("x", encoding="utf-8") as handle:
        json.dump(report,handle,sort_keys=True,indent=2)
        handle.write("\n")
    print("Stage244: single actual guest, 5 inprocess paired states, "
          "nanosecond cost per threat forecast:",
          report["guest_scene_values_ns"])


if __name__ == "__main__":
    main()
