#!/usr/bin/env python3
"""Stage233: prove guest-only right-stick risk visibility does not change battle."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image
from tools.foj_stage231_threat_guest_check import (
    read_frame, bounded_color_count, REGIONS, SAFE, DANGER, HERO, ENEMY,
)

METER=(57,161,229)
SCHEMA="foj-stage233-neXium-visual-threat-toggle-v1"


def count_near(frame: Image.Image, target: tuple[int,int,int]) -> int:
    palette=frame.getcolors(maxcolors=65536)
    if palette is None:
        raise ValueError("Unbounded emulator palette")
    return sum(n for n,rgb in palette
               if all(abs(rgb[c]-target[c])<=8 for c in range(3)))


def verify_toggle(files: tuple[Path,Path,Path,Path]) -> dict:
    screenshots=[read_frame(path) for path in files]
    safe=[bounded_color_count(im,REGIONS["safe"],SAFE) for im in screenshots]
    damage=[bounded_color_count(im,REGIONS["danger"],DANGER) for im in screenshots]
    hero=[count_near(im,HERO) for im in screenshots]
    enemy=[count_near(im,ENEMY) for im in screenshots]
    meter=[count_near(im,METER) for im in screenshots]
    if safe[0] or damage[0]:
        raise ValueError(f"Threat preview visible before hero selection: {safe}/{damage}")
    if not (10<=safe[1]<=36 and 10<=safe[3]<=36):
        raise ValueError(f"ON state lacks real guest safe marker: {safe}")
    if not (24<=damage[1]<=48 and 24<=damage[3]<=48):
        raise ValueError(f"ON state lacks both warning ticks: {damage}")
    if safe[2] or damage[2]:
        raise ValueError(f"Right-stick toggle failed to hide all risk marks: {safe}/{damage}")
    if abs(safe[1]-safe[3])>3 or abs(damage[1]-damage[3])>3:
        raise ValueError("Right-stick second toggle failed to restore identical warnings")
    if max(hero)-min(hero)>8 or max(enemy)-min(enemy)>8:
        raise ValueError("Visibility-only toggle changed the hero/enemy state")
    if meter[0]>3 or not 6<=meter[1]<=40:
        raise ValueError(f"Unrealistic initial/selected input history: {meter}")
    if max(meter[1:])-min(meter[1:])>3:
        raise ValueError(f"Display-only stick clicks modified the battle replay: {meter}")
    return {
        "schema":SCHEMA,"emulator":"NeXium","guest_screenshots":4,
        "safe_pixels":safe,"damage_pixels":damage,
        "hero_pixels":hero,"enemy_pixels":enemy,
        "battle_input_meter_pixels":meter,
        "show_hide_show_proven":True,
        "battle_state_unchanged_by_visibility_toggle":True,
        "original_ps3_assets_used":False,
        "physical_switch_tested":False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("initial","visible","hidden","restored"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    a=parser.parse_args()
    report=verify_toggle((a.initial,a.visible,a.hidden,a.restored))
    with a.report.open("x",encoding="utf-8") as destination:
        json.dump(report,destination,sort_keys=True,indent=2)
        destination.write("\n")
    print("Confirmed actual NeXium show/hide/show risk without gameplay inputs")


if __name__=="__main__":
    main()
