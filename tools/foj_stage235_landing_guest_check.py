#!/usr/bin/env python3
"""Stage235: fail closed unless actual NeXium guest shows predicted enemy cell."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from tools.foj_stage231_threat_guest_check import read_frame, bounded_color_count

MARKER=(185,127,236)
# In the 1280x720 synthetic test scene, the cursor's first valid
# (2,2) destination predicts enemy move from (6,3) -> (6,2).
# Guest scaling and X11 frame offset are bounded using a small tile region.
ENEMY_NEXT_RECT=(857,902,309,350)
SCHEMA="foj-stage235-nexium-generated-next-enemy-cell-v1"


def purple_in_frame(frame: Image.Image) -> int:
    palette=frame.getcolors(maxcolors=65536)
    if palette is None:
        raise ValueError("Unexpectedly noisy screenshot")
    return sum(amount for amount, rgb in palette
               if all(abs(rgb[i]-MARKER[i])<=10 for i in range(3)))


def verify_landing(frames: tuple[Path,Path,Path,Path,Path,Path]) -> dict:
    screenshots=[read_frame(path) for path in frames]
    counts=[purple_in_frame(im) for im in screenshots]
    region=[bounded_color_count(im,ENEMY_NEXT_RECT,MARKER)
            for im in screenshots]
    for index in (0,1,3,5):
        if counts[index] or region[index]:
            raise ValueError(f"Predicted enemy marker shown in invalid frame {index}: {counts}")
    if not (15<=counts[2]<=80 and 15<=counts[4]<=80):
        raise ValueError(f"Marker not present under valid hovered move: {counts}")
    if not (15<=region[2]<=80 and 15<=region[4]<=80):
        raise ValueError(f"Marker not near simulated enemy landing tile: {region}")
    if abs(counts[2]-region[2])>4 or abs(counts[4]-region[4])>4:
        raise ValueError("Marker pixels appear outside expected destination region")
    if abs(counts[2]-counts[4])>5:
        raise ValueError("Visibility-only RStick click changed predicted enemy cell")
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "actual_guest_frames": len(frames),
        "expected_hovered_hero_cell": [2,2],
        "expected_next_enemy_cell": [6,2],
        "guest_purple_pixels": counts,
        "expected_tile_region_pixels": region,
        "invalid_destination_clears_marker": True,
        "visibility_toggle_clears_and_restores_marker": True,
        "original_ps3_assets_used": False,
        "original_foj_enemy_ai_verified": False,
        "physical_switch_tested": False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("initial","selected","hovered","hidden","restored","blocked"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    result=verify_landing((
        args.initial,args.selected,args.hovered,args.hidden,
        args.restored,args.blocked,
    ))
    with args.report.open("x",encoding="utf-8") as destination:
        json.dump(result,destination,sort_keys=True,indent=2)
        destination.write("\n")
    print("Stage235: NeXium next-enemy-cell forecast marker verified")


if __name__=="__main__":
    main()
