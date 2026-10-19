#!/usr/bin/env python3
"""Stage243: ABBA cached/uncached guest render comparison with visual parity.

Measures only the 32-frame averaged *software renderer* microsecond value
inside a NeXium guest. No GPU/FPS/hardware timing or causal speedup assertion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from PIL import ImageChops
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage238_cache_guest_check import (
    STATES, ALL_GENERATIONS, IDLE, HIT, NO_HIT, GENERATION_RECT, HIT_RECT,
    matching,
)
from tools.foj_stage241_render_guest_check import (
    decode_microseconds, verify_render_timing, close,
)

SCHEMA = "foj-stage243-guest-abba-cached-render-v1"
ORDER = ("cached_first", "uncached_first", "uncached_second", "cached_second")
ROLES = ("cached", "uncached", "uncached", "cached")
MODE_X, MODE_Y = 520, (13, 15, 17)
MODE_CACHED = (17, 207, 241)
MODE_UNCACHED = (238, 94, 21)
# Screenshots in NeXium show framebuffer at 1280x720 plus an ~8px x offset.
# Take ONLY the actual game scene. Exclude all top-row diagnostic telemetry.
SCENE_CROP = (200, 48, 1150, 690)


def binary_sha_file(path: Path) -> str:
    digest = path.read_text(encoding="utf-8").split()
    if len(digest) < 1 or len(digest[0]) != 64 or not all(
            ch in "0123456789abcdef" for ch in digest[0]):
        raise ValueError(f"Invalid SHA-256 evidence: {path}")
    return digest[0]


def verify_uncached_markers(frame) -> None:
    counts = [matching(frame, color, GENERATION_RECT)
              for color in ALL_GENERATIONS]
    hit_count = matching(frame, HIT, HIT_RECT)
    no_hit = matching(frame, NO_HIT, HIT_RECT)
    if not (12 <= counts[0] <= 150 and all(c <= 4 for c in counts[1:])
            and hit_count <= 4 and 12 <= no_hit <= 150):
        raise ValueError(f"Experimental uncached NRO used cache: {counts}, {hit_count}, {no_hit}")


def inspect_sequence(folder: Path, role: str) -> dict:
    if role not in ("cached", "uncached"):
        raise ValueError("Invalid NRO build identity")
    paths = tuple(folder / f"cache-{s.replace('_', '-')}.png" for s in STATES)
    if role == "cached":
        verify_render_timing(paths)
    frame_hashes = []
    scene_hashes = []
    values = []
    expected_color = MODE_CACHED if role == "cached" else MODE_UNCACHED
    opposite = MODE_UNCACHED if role == "cached" else MODE_CACHED
    for state, path in zip(STATES, paths):
        im = read_frame(path)
        samples = [im.getpixel((MODE_X, y)) for y in MODE_Y]
        if not all(close(p, expected_color) for p in samples) or any(
                close(p, opposite) for p in samples):
            raise ValueError(f"{state}: wrong cached/uncached guest NRO mode tile: {samples}")
        if role == "uncached":
            verify_uncached_markers(im)
        values.append(decode_microseconds(path))
        frame_hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
        scene_hashes.append(hashlib.sha256(im.crop(SCENE_CROP).tobytes()).hexdigest())
    if len(set(frame_hashes)) != len(STATES):
        raise ValueError("Duplicate guest screenshots within one process")
    if len(set(values)) < 2:
        raise ValueError("Stale constant guest render time")
    log = folder / "guest.log"
    if not log.is_file() or log.stat().st_size == 0:
        raise ValueError("Guest process log missing")
    return {
        "role": role,
        "render_us": dict(zip(STATES, values)),
        "scene_sha256": dict(zip(STATES, scene_hashes)),
        "frame_sha256": dict(zip(STATES, frame_hashes)),
        "nro_sha256": binary_sha_file(folder / "nro.sha256"),
        "nexium_sha256": binary_sha_file(folder / "nexium-archive.sha256"),
    }


def summarize(results: dict[str, dict]) -> dict:
    if set(results) != set(ORDER):
        raise ValueError("ABBA requires exactly four independently booted guests")
    if any(results[key].get("role") != role
           for key, role in zip(ORDER, ROLES)):
        raise ValueError("Guest role does not match ABBA order")
    emulator_hashes = {r["nexium_sha256"] for r in results.values()}
    cached_hashes = {results[k]["nro_sha256"]
                     for k in ("cached_first", "cached_second")}
    uncached_hashes = {results[k]["nro_sha256"]
                       for k in ("uncached_first", "uncached_second")}
    if len(emulator_hashes) != 1 or len(cached_hashes) != 1 or len(uncached_hashes) != 1:
        raise ValueError("Emulator or NRO binaries differ within one ABBA experiment")
    if next(iter(cached_hashes)) == next(iter(uncached_hashes)):
        raise ValueError("Identical cached and uncached NRO files")
    reference = results["cached_first"]["scene_sha256"]
    for key in ORDER:
        if results[key]["scene_sha256"] != reference:
            raise ValueError(f"{key}: game-scene pixels disagree; no timing inference")
    if len({tuple(r["frame_sha256"].values())
            for r in results.values()}) != len(ORDER):
        raise ValueError("Reused screenshot evidence between different guests")
    per_state = {}
    for state in STATES:
        values = {key: results[key]["render_us"][state] for key in ORDER}
        if any(type(value) is not int or not 1 <= value < 65535
               for value in values.values()):
            raise ValueError(f"Missing or invalid guest timer: {state}")
        cached_mean = statistics.mean((values["cached_first"],
                                        values["cached_second"]))
        uncached_mean = statistics.mean((values["uncached_first"],
                                          values["uncached_second"]))
        per_state[state] = {
            "cached_pair_us": [values["cached_first"], values["cached_second"]],
            "uncached_pair_us": [values["uncached_first"], values["uncached_second"]],
            "cached_mean_us": cached_mean,
            "uncached_mean_us": uncached_mean,
            "uncached_minus_cached_us": uncached_mean - cached_mean,
            "observed_uncached_over_cached_ratio": round(uncached_mean / cached_mean, 4),
        }
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "guest_boot_order": list(ORDER),
        "independent_guest_processes": 4,
        "real_guest_screenshots": 4 * len(STATES),
        "comparison": "controlled ABBA of two compile-time NRO variants",
        "pair_results": per_state,
        "scene_pixels_identical_except_top_diagnostics": True,
        "guest_cache_state_verified": True,
        "same_neXium_binary": True,
        "nexium_archive_sha256": next(iter(emulator_hashes)),
        "cached_nro_sha256": next(iter(cached_hashes)),
        "uncached_nro_sha256": next(iter(uncached_hashes)),
        "timing_metric": "32-frame mean CPU software-render microseconds",
        "timing_clock": "emulated AArch64 armGetSystemTick/armTicksToNs",
        "physical_switch_hardware_tested": False,
        "switch_fps_measured": False,
        "gpu_time_measured": False,
        "full_frame_latency_measured": False,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
        "hard_speedup_threshold_enforced": False,
    }


def validate_artifacts(root: Path) -> dict:
    return summarize({
        key: inspect_sequence(root / key, role)
        for key, role in zip(ORDER, ROLES)
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    receipt = validate_artifacts(args.evidence_root)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(receipt, output, sort_keys=True, indent=2)
        output.write("\n")
    hover = receipt["pair_results"]["hovered"]
    print("Stage243: 4 independent NeXium guests, 36 actual frames, pixel parity; "
          "hover uncached/cached ratio",
          hover["observed_uncached_over_cached_ratio"],
          "(no FPS/hardware claim)")


if __name__ == "__main__":
    main()
