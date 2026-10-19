#!/usr/bin/env python3
"""Stage238: actual NeXium proof of risk-map cache reuse and invalidation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image

from tools.foj_stage231_threat_guest_check import read_frame

SCHEMA = "foj-stage238-nexium-threat-cache-guest-v1"
IDLE = (82, 92, 104)
FIRST = (41, 203, 220)
SECOND = (231, 178, 64)
OVERFLOW = (229, 71, 190)
HIT = (52, 223, 136)
NO_HIT = (114, 36, 196)
STATES = (
    "initial", "selected", "hovered", "hidden", "restored",
    "cancelled", "guarded", "guard_hovered", "ended",
)
EXPECTED_GENERATIONS = (
    IDLE, FIRST, FIRST, FIRST, FIRST, IDLE, SECOND, SECOND, IDLE,
)
EXPECTED_HITS = (
    NO_HIT, HIT, HIT, HIT, HIT, HIT, HIT, HIT, HIT,
)
ALL_GENERATIONS = (IDLE, FIRST, SECOND, OVERFLOW)


def near(candidate: tuple[int, int, int], color: tuple[int, int, int]) -> bool:
    return all(abs(candidate[c] - color[c]) <= 8 for c in range(3))


# Actual NeXium guest screenshots letterbox the 1280x720 framebuffer.
# The two Stage238 tiles appear at x=409..415 and x=420..427, y=12..18.
# Restrict classification to disjoint bounded neighborhoods. The old
# full-image histogram misclassified unrelated GUI pixels as cache state.
# Bounds are inclusive-left, exclusive-right, inclusive-top, exclusive-bottom.
GENERATION_RECT = (407, 418, 10, 21)
HIT_RECT = (419, 430, 10, 21)


def matching(frame: Image.Image, color: tuple[int, int, int],
             rect: tuple[int, int, int, int]) -> int:
    x1, x2, y1, y2 = rect
    return sum(
        near(frame.getpixel((x, y)), color)
        for y in range(y1, y2) for x in range(x1, x2)
    )


def verify_cache_screenshots(paths: tuple[Path, ...]) -> dict:
    if len(paths) != len(STATES):
        raise ValueError("Expected nine ordered guest screenshots")
    generations = []
    hits = []
    for index, path in enumerate(paths):
        image = read_frame(path)
        counts = [matching(image, rgb, GENERATION_RECT)
                  for rgb in ALL_GENERATIONS]
        counts.extend((matching(image, HIT, HIT_RECT),
                       matching(image, NO_HIT, HIT_RECT)))
        expected = ALL_GENERATIONS.index(EXPECTED_GENERATIONS[index])
        expected_hit = 4 if EXPECTED_HITS[index] == HIT else 5
        for i, amount in enumerate(counts):
            if i in (expected, expected_hit):
                if not 12 <= amount <= 150:
                    raise ValueError(
                        f"{STATES[index]} missing cache telemetry color {i}: {counts}")
            elif amount > 4:
                raise ValueError(
                    f"{STATES[index]} contains unexpected cache telemetry {i}: {counts}")
        generations.append(counts[:4])
        hits.append(counts[4:])
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "real_guest_screenshots": len(paths),
        "stage237_host_cache_parity_required": True,
        "initial_cache_empty": True,
        "single_generation_survives_hover_and_overlay_toggle": True,
        "cancel_drops_cached_matrix": True,
        "guard_reselection_recomputes_once": True,
        "post_guard_hover_reuses_second_matrix": True,
        "enemy_turn_drops_cached_matrix": True,
        "hit_counter_observed": True,
        "generation_pixels": generations,
        "hit_pixels": hits,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
        "physical_switch_tested": False,
        "fps_gain_measured": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--" + state.replace("_", "-"),
                            required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = verify_cache_screenshots(tuple(
        getattr(args, state) for state in STATES))
    with args.report.open("x", encoding="utf-8") as file:
        json.dump(report, file, sort_keys=True, indent=2)
        file.write("\n")
    print("Stage238: actual guest cache generations and hits verified")


if __name__ == "__main__":
    main()
