#!/usr/bin/env python3
"""Stage223: verify real NeXium screenshots show an enemy moving after Y.

Only invented 8x6 battle pixels are expected. Passing does not prove
authentic PS3 gameplay, original geometry, or physical Switch operation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

SCHEMA = "foj-stage223-synthetic-guest-enemy-movement-v1"
BACKGROUND = (13, 19, 33)
HERO = (95, 193, 244)
ENEMY = (227, 82, 93)
MAX_FRAMESIZE = (4096, 2160)
MIN_FRAMESIZE = (800, 500)


def load_pixels(path: Path) -> Image.Image:
    with Image.open(path) as source:
        image = source.convert("RGB")
    if not (MIN_FRAMESIZE[0] <= image.width <= MAX_FRAMESIZE[0] and
            MIN_FRAMESIZE[1] <= image.height <= MAX_FRAMESIZE[1]):
        raise ValueError("NeXium screenshot dimensions out of range")
    return image


def samples(image: Image.Image, rgb: tuple[int, int, int]) -> list[tuple[int, int]]:
    pixels = image.load()
    coords: list[tuple[int, int]] = []
    for y in range(image.height):
        for x in range(image.width):
            p = pixels[x, y]
            if all(abs(p[k] - rgb[k]) <= 12 for k in range(3)):
                coords.append((x, y))
    return coords


def center(coords: list[tuple[int, int]]) -> tuple[float, float]:
    return (sum(x for x, _ in coords) / len(coords),
            sum(y for _, y in coords) / len(coords))


def check_frames(files: tuple[Path, Path, Path]) -> dict:
    frames = [load_pixels(path) for path in files]
    if len({frame.size for frame in frames}) != 1:
        raise ValueError("Guest frames must share dimensions")
    centers: list[tuple[float, float]] = []
    for frame in frames:
        if len(samples(frame, BACKGROUND)) < 2500:
            raise ValueError("Expected synthetic battle background is missing")
        if len(samples(frame, HERO)) < 100:
            raise ValueError("Expected blue synthetic hero token is missing")
        enemy = samples(frame, ENEMY)
        if len(enemy) < 100:
            raise ValueError("Expected red synthetic enemy token is missing")
        centers.append(center(enemy))
    delta = []
    for before, after in zip(centers, centers[1:]):
        dx, dy = after[0] - before[0], after[1] - before[1]
        if abs(dx) + abs(dy) < 18:
            raise ValueError("Enemy pixel centroid did not move after Y")
        if abs(dx) > 400 or abs(dy) > 250:
            raise ValueError("Implausible enemy displacement after one turn")
        delta.append([round(dx, 3), round(dy, 3)])
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "screenshots_compared": 3,
        "guest_frame_dimensions": list(frames[0].size),
        "enemy_displacement_after_each_emulated_y": delta,
        "guest_enemy_moves_after_y": True,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
        "physical_switch_execution_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--turn1", type=Path, required=True)
    parser.add_argument("--turn2", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = check_frames((args.initial, args.turn1, args.turn2))
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("Verified two actual NeXium Y-driven enemy transitions; "
          "synthetic battle only.")


if __name__ == "__main__":
    main()
