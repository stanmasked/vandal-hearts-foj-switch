#!/usr/bin/env python3
"""Stage226: evidence for A-move, B-undo, alternate A-move in actual NeXium.

All screenshots are from the same generated-only 8x6 homebrew guest.
Pixel signatures are not evidence for original PS3 functionality.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

COLORS = {
    "background": (13, 19, 33),
    "hero": (95, 193, 244),
    "enemy": (227, 82, 93),
    "can_undo": (113, 241, 201),
}
SCHEMA = "foj-stage226-nexium-synthetic-b-move-undo-v1"


def read(path: Path) -> Image.Image:
    with Image.open(path) as f:
        rgb = f.convert("RGB")
    if not (800 <= rgb.width <= 4096 and 500 <= rgb.height <= 2160):
        raise ValueError("Unsupported NeXium screenshot dimensions")
    return rgb


def points(frame: Image.Image, rgb: tuple[int, int, int]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    pix = frame.load()
    for y in range(frame.height):
        for x in range(frame.width):
            value = pix[x, y]
            if all(abs(value[i] - rgb[i]) <= 10 for i in range(3)):
                result.append((x, y))
    return result


def center(pixels: list[tuple[int, int]]) -> tuple[float, float]:
    return (sum(x for x, _ in pixels) / len(pixels),
            sum(y for _, y in pixels) / len(pixels))


def l1(a: tuple[float, float], b: tuple[float, float]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def verify_undo(files: tuple[Path, Path, Path, Path]) -> dict:
    initial, moved, undone, alternate = [read(p) for p in files]
    frames = (initial, moved, undone, alternate)
    if len({frame.size for frame in frames}) != 1:
        raise ValueError("Four guest captures have inconsistent dimensions")

    states: list[dict[str, list[tuple[int, int]]]] = []
    for frame in frames:
        state = {key: points(frame, value) for key, value in COLORS.items()}
        if (len(state["background"]) < 2500 or
            len(state["hero"]) < 100 or len(state["enemy"]) < 100):
            raise ValueError("Frame missing expected invented battle scene")
        states.append(state)

    undo_pixels = [len(state["can_undo"]) for state in states]
    if not (undo_pixels[0] < 5 and undo_pixels[1] >= 35 and
            undo_pixels[2] < 5 and undo_pixels[3] >= 35):
        raise ValueError("Undo marker did not track A move / B undo / new A move")

    hero = [center(state["hero"]) for state in states]
    enemy = [center(state["enemy"]) for state in states]
    if l1(hero[0], hero[1]) < 18:
        raise ValueError("First A move not visible in guest hero centroid")
    if l1(hero[0], hero[2]) > 5:
        raise ValueError("B failed to restore original hero location")
    if l1(hero[0], hero[3]) < 12 or l1(hero[1], hero[3]) < 12:
        raise ValueError("New route after undo is not a distinct hero position")
    if any(l1(enemy[0], position) > 4 for position in enemy[1:]):
        raise ValueError("Enemy moved during hero-only controls")

    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "guest_frames": 4,
        "initial_hero_restored_after_b": True,
        "alternate_route_accepted": True,
        "undo_marker_in_guest_frames": undo_pixels,
        "hero_centroids": [[round(x, 2), round(y, 2)] for x, y in hero],
        "physical_switch_tested": False,
        "original_ps3_assets_used": False,
        "source_game_movement_rules_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--moved", type=Path, required=True)
    parser.add_argument("--undone", type=Path, required=True)
    parser.add_argument("--alternate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    a = parser.parse_args()
    result = verify_undo((a.initial, a.moved, a.undone, a.alternate))
    with a.report.open("x", encoding="utf-8") as out:
        json.dump(result, out, sort_keys=True, indent=2)
        out.write("\n")
    print("NeXium guest B-undo restored hero; alternate A move confirmed.")


if __name__ == "__main__":
    main()
