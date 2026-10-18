#!/usr/bin/env python3
"""Stage229: require actual NeXium replay input count to follow B undo sequence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image

from tools.foj_stage226_undo_guest_check import verify_undo

METER_RGB = (57, 161, 229)
SCHEMA = "foj-stage229-neXium-guest-input-counter-v1"
EXPECTED_INPUTS = (0, 4, 5, 8)


def count_filled(path: Path) -> int:
    with Image.open(path) as image:
        frame = image.convert("RGB")
    palette = frame.getcolors(maxcolors=65536)
    samples = palette if palette is not None else ((1, rgb) for rgb in frame.getdata())
    return sum(n for n, rgb in samples
               if all(abs(rgb[i] - METER_RGB[i]) <= 8 for i in range(3)))


def verify_meter(frames: tuple[Path, Path, Path, Path]) -> dict:
    # A loaded screen with no movement is NOT accepted as a replay proof.
    movement = verify_undo(frames)
    values = [count_filled(f) for f in frames]
    if values[0] > 4:
        raise ValueError("Replay meter nonempty before first controller input")
    if not (values[1] > values[0] and values[2] > values[1]
            and values[3] > values[2]):
        raise ValueError("Replay meter failed to advance for A/B inputs")
    # Infer display scaling from the first nonzero count, not the final
    # count (whose manipulation is one of the attacks being detected).
    scale = values[1] / EXPECTED_INPUTS[1]
    if not 6 <= scale <= 40:
        raise ValueError("Replay meter display has implausible pixel scale")
    for i, count in enumerate(EXPECTED_INPUTS[1:], 1):
        if abs(values[i] - scale * count) > max(5, scale * 0.35):
            raise ValueError(f"Wrong replay command count in frame {i}")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "expected_input_counts": list(EXPECTED_INPUTS),
        "guest_replay_meter_pixels": values,
        "input_pixel_scale": round(scale, 3),
        "movement_undo_verified": movement["initial_hero_restored_after_b"],
        "original_game_assets_used": False,
        "original_ps3_gameplay_verified": False,
        "physical_switch_tested": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--moved", type=Path, required=True)
    parser.add_argument("--undone", type=Path, required=True)
    parser.add_argument("--alternate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify_meter((args.initial,args.moved,args.undone,args.alternate))
    with args.report.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2, sort_keys=True)
        out.write("\n")
    print("NeXium replay command meter validated: 0,4,5,8 events")


if __name__ == "__main__":
    main()
