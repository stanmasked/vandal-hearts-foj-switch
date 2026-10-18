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

# Shared core/isometric_demo.c projection for generated tile coordinates.
# Tile (2,2), elevation1 -> (640,222); tile (5,2), elevation1 -> (802,312).
# Markers are deliberately drawn after terrain and path previews.
PIXELS = {"safe": (653, 233), "damage_one": (811, 323),
          "damage_two": (817, 323)}
SCHEMA = "foj-stage231-nexium-generated-attack-risk-guest-v1"


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


def check_preview(frames: tuple[Path, Path, Path, Path, Path]) -> dict:
    initial, selected, cursor, cancelled, guarded = [read_frame(x) for x in frames]
    details = {
        name: [image.getpixel(xy) for image in
               (initial, selected, cursor, cancelled, guarded)]
        for name, xy in PIXELS.items()
    }
    for marker, rgb in (("safe", SAFE), ("damage_one", DANGER),
                        ("damage_two", DANGER)):
        sampled = details[marker]
        if close(sampled[0], rgb):
            raise ValueError("Risk marker present before selecting hero")
        if not close(sampled[1], rgb) or not close(sampled[2], rgb):
            raise ValueError(f"Risk marker {marker} not stable under cursor movement")
        if close(sampled[3], rgb):
            raise ValueError("Risk marker survived B deselection")
    if not close(details["safe"][4], SAFE):
        raise ValueError("Guarding unexpectedly removed safe preview")
    if not close(details["damage_one"][4], DANGER):
        raise ValueError("Guarding unexpectedly erased all predicted damage")
    if close(details["damage_two"][4], DANGER):
        raise ValueError("Guarding did not reduce two orange HP ticks to one")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "actual_guest_screenshots": 5,
        "safe_move_mark_visible_on_selection": True,
        "two_hp_damage_preview_visible": True,
        "cursor_does_not_remove_preview": True,
        "cancel_clears_preview": True,
        "guard_reduces_expected_damage_to_one_hp": True,
        "samples": details,
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
