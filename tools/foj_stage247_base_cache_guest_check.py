#!/usr/bin/env python3
"""Stage247: require authentic nine-state NeXium cache reuse on 32-frame HUD."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage241_render_guest_check import close
from tools.foj_stage246_phase_guest_check import (
    PHASES, sample_x, verify_phase_screenshots,
)

SCHEMA = "foj-stage247-nexium-scene-keyed-software-base-cache-v1"
HIT_RGB = (42, 231, 131)
MISS_RGB = (242, 49, 49)
TILE_X = 1252
TILE_Y = (13, 15, 17)

def classify_cache_tile(image) -> bool:
    x_positions = (sample_x(TILE_X + offset) for offset in (2, 3, 4))
    samples = [image.getpixel((x, y)) for x in x_positions for y in TILE_Y]
    if all(close(p, HIT_RGB) for p in samples):
        return True
    if all(close(p, MISS_RGB) for p in samples):
        return False
    raise ValueError("Stage247 real-frame base-cache tile missing or inconsistent")

def verify_base_cache_guest(paths: tuple[Path, ...]) -> dict:
    # Re-run the prior Stage238 tactical/cache state and Stage241/246
    # full/partitioned timing proofs. A green tile alone is insufficient.
    phase = verify_phase_screenshots(paths)
    states = {}
    digests = {}
    for state, path in zip(STATES, paths):
        image = read_frame(path)
        hit = classify_cache_tile(image)
        if not hit:
            raise ValueError(f"{state}: base-cache was cold after the state dwell")
        states[state] = {
            "base_reused_on_snapshot": True,
            "terrain_mean_us": phase["states"][state]["terrain"],
            "total_exclusive_phase_us": phase["states"][state]["measured_sum_us"],
        }
        digests[state] = hashlib.sha256(path.read_bytes()).hexdigest()
    active = ("selected", "hovered", "restored", "guarded", "guard_hovered")
    inactive = ("initial", "hidden", "cancelled", "ended")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "authentic_screenshot_count": len(paths),
        "warm_base_cache_proofs": len(states),
        "cache_mode": "scene-exact final base raster, threat/HUD painted each frame",
        "phase_proof_schema": phase["schema"],
        "scene_states": states,
        "frame_sha256": digests,
        "active_terrain_median_us": statistics.median(
            states[x]["terrain_mean_us"] for x in active),
        "inactive_terrain_median_us": statistics.median(
            states[x]["terrain_mean_us"] for x in inactive),
        "has_original_ps3_assets": False,
        "physical_switch_tested": False,
        "gpu_or_fps_measured": False,
        "end_to_end_frame_latency_measured": False,
        "actual_game_speedup_proven": False,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--" + state.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = verify_base_cache_guest(tuple(getattr(args, s) for s in STATES))
    with args.report.open("x", encoding="utf-8") as out:
        json.dump(result, out, sort_keys=True, indent=2)
        out.write("\n")
    print("Stage247: 9/9 real guest base-cache hits, 32-frame terrain medians",
          result["active_terrain_median_us"],
          result["inactive_terrain_median_us"])

if __name__ == "__main__":
    main()
