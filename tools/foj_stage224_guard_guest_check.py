#!/usr/bin/env python3
"""Stage224: compare two real NeXium synthetic battle outcomes.

The same 8x6 starting state is reached in two independent guest sessions.
Both move the hero four tiles; only one presses ZR before ending the
turn. Visible guard indicator and the post-turn HP pixel delta must
match the invented 2-vs-1 HP rule. Never claim PS3 combat fidelity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

MIN_SIZE = (800, 500)
MAX_SIZE = (4096, 2160)
PALETTE = {
    "background": (13, 19, 33),
    "hero": (95, 193, 244),
    "enemy": (227, 82, 93),
    "guard": (38, 209, 143),
}
SCHEMA = "foj-stage224-nexium-synthetic-guard-damage-v1"


def open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as original:
        frame = original.convert("RGB")
    if not (MIN_SIZE[0] <= frame.width <= MAX_SIZE[0] and
            MIN_SIZE[1] <= frame.height <= MAX_SIZE[1]):
        raise ValueError("Unexpected NeXium frame dimensions")
    return frame


def marker_points(frame: Image.Image,
                  color: tuple[int, int, int]) -> list[tuple[int, int]]:
    matches = []
    pixels = frame.load()
    for y in range(frame.height):
        for x in range(frame.width):
            rgb = pixels[x, y]
            if all(abs(rgb[i] - color[i]) <= 10 for i in range(3)):
                matches.append((x, y))
    return matches


def center(points: list[tuple[int, int]]) -> tuple[float, float]:
    return sum(x for x, _ in points) / len(points), sum(
        y for _, y in points) / len(points)


def compare_guard_frames(guard_active: Path, guarded_end: Path,
                         normal_end: Path) -> dict:
    frames = [open_rgb(p) for p in
              (guard_active, guarded_end, normal_end)]
    if len({f.size for f in frames}) != 1:
        raise ValueError("Guard comparison requires same-size guest frames")

    counts: list[dict[str, int]] = []
    positions: list[dict[str, tuple[float, float]]] = []
    for frame in frames:
        color_points = {name: marker_points(frame, rgb)
                        for name, rgb in PALETTE.items()}
        cs = {name: len(pts) for name, pts in color_points.items()}
        if cs["background"] < 2500 or cs["hero"] < 200 or cs["enemy"] < 150:
            raise ValueError("Expected synthetic battle pixels missing")
        counts.append(cs)
        positions.append({key: center(color_points[key])
                          for key in ("hero", "enemy")})

    if counts[0]["guard"] < 35:
        raise ValueError("ZR did not show the active guard marker")
    if counts[1]["guard"] > 5 or counts[2]["guard"] > 5:
        raise ValueError("Guard marker failed to expire after Y")
    difference = counts[1]["hero"] - counts[2]["hero"]
    # 8 maximum HP, 40-unit blue bar, five pixel rows:
    # normal 6HP = 30 columns, guarded 7HP = 35: +25px native.
    # Tolerate bounded desktop scaling but reject equal/not-less damage.
    if not 12 <= difference <= 100:
        raise ValueError("Guarded turn did not retain expected extra hero HP")

    # Distinguish a health-bar difference from a different scene/position.
    for token in ("hero", "enemy"):
        ax, ay = positions[1][token]
        bx, by = positions[2][token]
        if abs(ax - bx) > 4 or abs(ay - by) > 4:
            raise ValueError("Compared guest turns have different unit positions")

    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "gameplay_scope": "invented_synthetic_8x6_battle",
        "guard_marker_seen_before_y": True,
        "guard_marker_expired_after_y": True,
        "guarded_minus_normal_hero_blue_pixels": difference,
        "same_enemy_and_hero_positions": True,
        "original_ps3_assets_used": False,
        "authentic_foj_damage_verified": False,
        "physical_switch_execution_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active", type=Path, required=True)
    parser.add_argument("--guarded", type=Path, required=True)
    parser.add_argument("--normal", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = compare_guard_frames(args.active, args.guarded, args.normal)
    with args.report.open("x", encoding="utf-8") as output:
        json.dump(result, output, sort_keys=True, indent=2)
        output.write("\n")
    print("Verified guarded vs unguarded NeXium synthetic battle damage.")


if __name__ == "__main__":
    main()
