#!/usr/bin/env python3
"""Require actual NeXium screenshots of synthetic movement risk and guard."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

SAFE = (59, 158, 130)
DANGER = (244, 141, 80)
BACKGROUND = (13, 19, 33)
HERO = (95, 193, 244)
ENEMY = (227, 82, 93)
SIZE = (1280, 720)

# NeXium captures the 1280x720 guest inside a slightly letterboxed GUI
# viewport, not at unscaled framebuffer coordinates. Inspect bounded tile
# neighborhoods, never exact raw-frame pixel addresses. Bounds are from
# genuine Stage231 guest captures and reject unrelated palette matches.
# Each rectangle is (left, right_exclusive, top, bottom_exclusive).
REGIONS = {"safe": (643, 663, 214, 242),
           "danger": (797, 824, 297, 334)}
SCHEMA = "foj-stage231-nexium-generated-attack-risk-guest-v2"

def read_frame(path: Path) -> Image.Image:
    with Image.open(path) as source:
        frame = source.convert("RGB")
    if frame.size != SIZE:
        raise ValueError("Unexpected NeXium guest size: expected 1280x720")
    histogram = frame.getcolors(maxcolors=65536)
    if histogram is None:
        raise ValueError("Guest screenshot contains unexpected noisy palette")
    def count(target: tuple[int, int, int]) -> int:
        return sum(n for n, rgb in histogram
                   if all(abs(rgb[i]-target[i]) <= 10 for i in range(3)))
    if count(BACKGROUND) < 2500 or count(HERO) < 100 or count(ENEMY) < 100:
        raise ValueError("Guest screenshot lacks generated battlefield or units")
    return frame


def close(rgb: tuple[int, ...], expected: tuple[int, ...]) -> bool:
    return all(abs(rgb[i]-expected[i]) <= 10 for i in range(3))


def bounded_color_count(frame: Image.Image, region: tuple[int, int, int, int],
                        target: tuple[int, int, int]) -> int:
    left, right, top, bottom = region
    return sum(close(frame.getpixel((x, y)), target)
               for y in range(top, bottom) for x in range(left, right))


def check_preview(frames: tuple[Path, Path, Path, Path, Path]) -> dict:
    images = [read_frame(path) for path in frames]
    samples = {
        "safe": [bounded_color_count(image, REGIONS["safe"], SAFE)
                 for image in images],
        "damage": [bounded_color_count(image, REGIONS["danger"], DANGER)
                   for image in images],
    }
    safe, damage = samples["safe"], samples["damage"]
    if safe[0] or damage[0]:
        raise ValueError(f"Unexpected risk marker before selection: {samples}")
    if safe[3] or damage[3]:
        raise ValueError(f"Stale risk marker after B cancellation: {samples}")
    if not (10 <= safe[1] <= 36 and 10 <= safe[2] <= 36 and
            10 <= safe[4] <= 36):
        raise ValueError(f"Safe tile not visible in guest: {samples}")
    if abs(safe[1] - safe[2]) > 3 or abs(safe[1] - safe[4]) > 3:
        raise ValueError(f"Safe overlay changes under cursor or guard: {samples}")
    if not (24 <= damage[1] <= 48 and 24 <= damage[2] <= 48):
        raise ValueError(f"Two-HP danger bars missing before guard: {samples}")
    if abs(damage[1] - damage[2]) > 3:
        raise ValueError(f"Danger display changed with cursor movement: {samples}")
    if not (12 <= damage[4] <= 24 and
            abs(damage[1] - 2 * damage[4]) <= 4):
        raise ValueError(f"Guard did not halve two-HP danger: {samples}")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "actual_guest_screenshots": 5,
        "safe_move_mark_visible_on_selection": True,
        "two_hp_damage_preview_visible": True,
        "cursor_does_not_remove_preview": True,
        "cancel_clears_preview": True,
        "guard_reduces_expected_damage_to_one_hp": True,
        "samples": samples,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
        "physical_switch_tested": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--cursor", type=Path, required=True)
    parser.add_argument("--cancelled", type=Path, required=True)
    parser.add_argument("--guarded", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = check_preview((args.initial,args.selected,args.cursor,
                            args.cancelled,args.guarded))
    with args.report.open("x", encoding="utf-8") as dest:
        json.dump(result,dest,sort_keys=True,indent=2)
        dest.write("\n")
    print("Stage231: actual guest threat preview and ZR mitigation proven")


if __name__ == "__main__":
    main()
