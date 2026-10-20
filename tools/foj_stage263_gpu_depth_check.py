#!/usr/bin/env python3
"""Fail-closed REAL NeXium occlusion proof for two draw-order adversaries.

One NRO (with a real Z24S8 target) is run twice against two entirely invented
FOJRM model depth arrangements. Material draw order is ALWAYS warm then cool:
 * warm-near / cool-far must show WARM at overlap even though warm draws first
 * cool-near / warm-far must show COOL at overlap, and both wings remain visible
The checker is never allowed to replace guest captures with PIL unit images.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops

from tools.foj_stage260_generated_gpu_sd import COLORS
from tools.foj_stage263_generated_depth_sd import PROBES

SCHEMA="foj.stage263.gpu_depth_guest.v1"
TOLERANCE=20
MIN_MATCH=85
POINTS={"warm_only":"warm","cool_only":"cool"}
FRAME_NAMES=("gpu-initial.png","gpu-later.png")


def matches(observed:tuple,expected:tuple)->bool:
    return all(abs(int(observed[i])-int(expected[i]))<=TOLERANCE
               for i in range(3))


def inspect(image_path:Path,near:str)->dict:
    if near not in ("warm","cool"):
        raise ValueError("Unknown depth ordering scenario")
    with Image.open(image_path) as f:
        rgb=f.convert("RGB")
    if rgb.size!=(1280,720):
        raise ValueError("Expected 1280x720 actual guest image")
    px=rgb.load()
    out={}
    for name,expected_material in (
        ("warm_only","warm"),("cool_only","cool"),("overlap",near)
    ):
        x,y=PROBES[name]
        expected=COLORS[0 if expected_material=="warm" else 1]
        wrong=COLORS[1 if expected_material=="warm" else 0]
        # Interior 11x11 samples; not close to triangle raster boundaries.
        samples=[px[xx,yy] for yy in range(y-5,y+6)
                 for xx in range(x-5,x+6)]
        good=sum(matches(rgb,expected) for rgb in samples)
        bad=sum(matches(rgb,wrong) for rgb in samples)
        if good<MIN_MATCH or bad>5:
            raise ValueError(
                f"Depth probe {name} wrong for {near}-near: "
                f"expected {expected_material}; got {good} correct and "
                f"{bad} opposite samples")
        out[name]={
            "pixel":[x,y],
            "expected_material":expected_material,
            "matching_samples":good,
            "other_material_samples":bad,
        }
    return out


def check_frames(folder:Path,near:str)->dict:
    first=inspect(folder/FRAME_NAMES[0],near)
    second=inspect(folder/FRAME_NAMES[1],near)
    for key in first:
        if abs(first[key]["matching_samples"]-
               second[key]["matching_samples"])>10:
            raise ValueError("Inconsistent depth presentation across frames")
    with Image.open(folder/FRAME_NAMES[0]) as a, Image.open(folder/FRAME_NAMES[1]) as b:
        one=a.convert("RGB");two=b.convert("RGB")
    if ImageChops.difference(one,two).getbbox() is None:
        raise ValueError("Duplicated guest framebuffer")
    # Clear color phase must visibly change outside both triangles.
    samples=((25,310),(1220,310),(640,650),(25,650))
    if sum(one.getpixel(p)!=two.getpixel(p) for p in samples)<3:
        raise ValueError("Guest frames do not show two distinct phases")
    return {"first":first,"second":second,
            "independent_gpu_clear_frames":True}


def verify(root:Path)->dict:
    warm=check_frames(root/"warm","warm")
    cool=check_frames(root/"cool","cool")
    if warm["first"]["overlap"]["expected_material"]!="warm" or (
       cool["first"]["overlap"]["expected_material"]!="cool"):
        raise ValueError("Depth reversal did not change overlap winner")
    return {
        "schema":SCHEMA,
        "actual_guest_frames_verified":4,
        "generated_only":True,
        "near_first_wins_over_later_draw":True,
        "near_second_wins_over_earlier_draw":True,
        "draw_order_independent_occlusion":True,
        "depth_scenarios":{"warm_near":warm,"cool_near":cool},
        "original_ps3_asset_loaded":False,
        "physical_switch_depth_tested":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        data=verify(args.evidence)
        with args.report.open("x",encoding="utf-8") as f:
            json.dump(data,f,indent=2,sort_keys=True);f.write("\n")
    except (ValueError,OSError) as exc:
        p.error("Actual NeXium GPU depth proof failed: "+str(exc))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
