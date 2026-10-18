#!/usr/bin/env python3
"""Stage227: independently check the actual NeXium guest reaches a synthetic victory.

Six screenshots are captured from one running Switch research NRO. Only
generated homebrew behavior is in scope; no PS3 gameplay is inferred.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image

PALETTE = {
    "background": (13, 19, 33),
    "hero": (95, 193, 244),
    "enemy": (227, 82, 93),
    "victory": (56, 185, 127),
}
SCHEMA = "foj-stage227-guest-synthetic-complete-victory-v1"


def colors(path: Path) -> tuple[tuple[int, int], dict[str, int]]:
    with Image.open(path) as loaded:
        image = loaded.convert("RGB")
    if not (800 <= image.width <= 4096 and 500 <= image.height <= 2160):
        raise ValueError("Guest framebuffer dimensions out of bounds")
    counts = {name: 0 for name in PALETTE}
    for pixel in image.getdata():
        for name, rgb in PALETTE.items():
            if all(abs(int(pixel[i]) - rgb[i]) <= 10 for i in range(3)):
                counts[name] += 1
    return image.size, counts


def verify_victory(frames: tuple[Path, ...]) -> dict:
    if len(frames) != 6:
        raise ValueError("Six actual guest screens are required")
    samples = [colors(path) for path in frames]
    if len({size for size, _ in samples}) != 1:
        raise ValueError("Guest images have inconsistent dimensions")
    counts = [values for _, values in samples]
    for i, palette in enumerate(counts):
        if palette["background"] < 2500 or palette["hero"] < 100:
            raise ValueError(f"Missing battlefield or hero in guest frame {i}")
    for i in range(4):
        if counts[i]["enemy"] < 150:
            raise ValueError(f"Enemy missing before victory in guest frame {i}")
        if counts[i]["victory"] > 60:
            raise ValueError("Victory marker appeared before killing enemy")
    for i in (4, 5):
        if counts[i]["victory"] < 400:
            raise ValueError("Final green victory strip is missing")
        if counts[i]["enemy"] > 20:
            raise ValueError("Enemy remains visibly alive after victory")

    # Both Y turns must hurt the hero by the same synthetic two-HP hit.
    turn1_blue = counts[1]["hero"]
    turn2_blue = counts[3]["hero"]
    if not 20 <= turn1_blue - turn2_blue <= 140:
        raise ValueError("Second actual enemy turn did not reduce blue HP")
    # Between the two Y turns the X attack must reduce enemy red HP.
    if not 30 <= counts[1]["enemy"] - counts[2]["enemy"] <= 160:
        raise ValueError("First X hit did not visibly reduce enemy HP")
    # The first hit must not end the battle; the second X must do so.
    if abs(counts[2]["enemy"] - counts[3]["enemy"]) > 20:
        raise ValueError("Enemy changed unexpectedly between first hit and next Y")
    # Y after terminal victory is rejected, so the same two sprite/HP
    # signatures should persist. Allow up to 5 desktop conversion pixels.
    for name in ("hero", "enemy", "victory"):
        if abs(counts[4][name] - counts[5][name]) > 5:
            raise ValueError("Post-victory Y changed the finished battle")

    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "frame_size": list(samples[0][0]),
        "actual_guest_screenshots": 6,
        "first_x_hit_reduced_enemy_hp": True,
        "second_y_hit_reduced_hero_hp": True,
        "second_x_resulted_in_victory": True,
        "terminal_y_was_rejected": True,
        "sprite_colors_by_frame": counts,
        "original_ps3_assets_used": False,
        "original_foj_rules_verified": False,
        "physical_switch_tested": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--after-turn1", type=Path, required=True)
    parser.add_argument("--after-hit1", type=Path, required=True)
    parser.add_argument("--after-turn2", type=Path, required=True)
    parser.add_argument("--victory", type=Path, required=True)
    parser.add_argument("--after-terminal-y", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    a = parser.parse_args()
    outcome = verify_victory((
        a.initial, a.after_turn1, a.after_hit1, a.after_turn2,
        a.victory, a.after_terminal_y,
    ))
    with a.report.open("x", encoding="utf-8") as destination:
        json.dump(outcome, destination, sort_keys=True, indent=2)
        destination.write("\n")
    print("Stage227: actual NeXium synthetic battle victory confirmed.")


if __name__ == "__main__":
    main()
