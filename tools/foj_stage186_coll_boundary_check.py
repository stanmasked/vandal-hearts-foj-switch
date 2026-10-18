#!/usr/bin/env python3
"""Stage 186: real NeXium guest COLL boundary/corner and zoom clamp tests.

Each screenshot is checked against the generated C heatmap at the expected
cursor, tile size and channel. Separate repeated-input screenshots must be
unchanged: validating only a screenshot is not enough for a clamp claim.
No original PS3 assets, no physical Switch testing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.foj_stage184_coll_input_check import (
    anchor, difference, load, source_pixel_agreement,
)

SCHEMA = "foj-stage186-nexium-coll-cursor-zoom-bounds-v1"
STATES = (
    ("left-edge", 0, 25, 12),
    ("top-edge", 0, 0, 12),
    ("min-zoom", 0, 0, 4),
    ("max-zoom", 0, 0, 30),
    ("right-edge", 49, 0, 30),
    ("bottom-edge", 49, 49, 30),
)


def verify_bounds(root: Path) -> dict:
    previous = load(root / "coll-reverse-left.png")
    anchor(previous)
    results = {}
    for state, x, y, tile in STATES:
        actual = load(root / f"coll-{state}.png")
        repeated = load(root / f"coll-{state}-repeat.png")
        expected = load(root / f"ref-coll-{state}.png")
        score, sampled = source_pixel_agreement(actual, expected)
        score_repeat, sampled_repeat = source_pixel_agreement(repeated, expected)
        change = difference(previous, actual)
        repeated_change = difference(actual, repeated)
        # The guest must visibly react to the first navigation, while
        # additional outward buttons at a boundary must be no-ops.
        # Both the initial and repeated frames must match source pixels.
        if (score < .87 or score_repeat < .87 or
            change < 100 or
            repeated_change > max(4000, actual.width * actual.height // 100)):
            raise ValueError("NeXium guest boundary/zoom clamp mismatch: " + state)
        results[state] = {
            "cursor": [x, y],
            "tile_size": tile,
            "source_channel": 0,
            "initial_reference_agreement": round(score, 5),
            "repeated_reference_agreement": round(score_repeat, 5),
            "reference_pixels_checked": sampled,
            "repeated_reference_pixels_checked": sampled_repeat,
            "changed_pixels_on_first_action": change,
            "changed_pixels_after_extra_outward_presses": repeated_change,
        }
        previous = repeated

    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "research_scope": "generated_only_coll_research_homebrew",
        "states_verified": results,
        "verified_cursor_minimum": [0, 0],
        "verified_cursor_maximum": [49, 49],
        "verified_tile_size_minimum": 4,
        "verified_tile_size_maximum": 30,
        "verified_repeat_at_bounds_has_no_effect": True,
        "original_ps3_assets_used": False,
        "authentic_foj_collision_semantics_verified": False,
        "physical_switch_execution_verified": False,
        "physical_gpu_scanout_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = verify_bounds(args.evidence)
        with args.report.open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print("NeXium six COLL edge and zoom states, including repeated no-ops, verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
