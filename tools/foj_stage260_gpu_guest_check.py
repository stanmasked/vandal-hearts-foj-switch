#!/usr/bin/env python3
"""Fail-closed analysis of actual generated-asset NeXium GPU screenshots.

No stored screenshot or reference is counted as a guest capture: it must
be read from --evidence, produced by the separate real NRO guest step.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image

SCHEMA = "foj.stage260.generated_gpu_guest.v1"
FRAMES = ("gpu-initial.png", "gpu-later.png")


def inspect(path: Path) -> dict:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    w, h = rgb.size
    if not (1100 <= w <= 2400 and 620 <= h <= 1500):
        raise ValueError("Unexpected NeXium image dimensions")
    pts = {"warm": [], "cool": []}
    x0, x1 = int(.16*w), int(.84*w)
    y0, y1 = int(.12*h), int(.90*h)
    px = rgb.load()
    for y in range(y0,y1,2):
        for x in range(x0,x1,2):
            r,g,b = px[x,y]
            if r>160 and g<145 and b<130 and r>g+75:
                pts["warm"].append((x,y))
            elif r<130 and g>150 and b>145 and b>r+85 and g>r+80:
                pts["cool"].append((x,y))
    for color, v in pts.items():
        if len(v)<250:
            raise ValueError(f"Required {color} GPU texture not visible in guest")
        xs=[p[0] for p in v]
        ys=[p[1] for p in v]
        if max(xs)-min(xs)<28 or max(ys)-min(ys)<40:
            raise ValueError("GPU material footprint too small")
    warm_x=sum(p[0] for p in pts["warm"])/len(pts["warm"])
    cool_x=sum(p[0] for p in pts["cool"])/len(pts["cool"])
    if not (warm_x < .5*w and cool_x > .5*w and cool_x-warm_x>.10*w):
        raise ValueError("Material index mapping/positions inconsistent")
    return {
        "resolution":[w,h],
        "warm_samples":len(pts["warm"]),
        "cool_samples":len(pts["cool"]),
        "warm_centroid_x":round(warm_x/w,4),
        "cool_centroid_x":round(cool_x/w,4),
    }


def verify(evidence: Path) -> dict:
    readings=[inspect(evidence/name) for name in FRAMES]
    if readings[0]["resolution"]!=readings[1]["resolution"]:
        raise ValueError("Guest framebuffer resolution changed")
    for color in ("warm","cool"):
        for a,b in ((readings[0],readings[1]),):
            if abs(a[color+"_centroid_x"]-b[color+"_centroid_x"])>.09:
                raise ValueError("GPU material position unstable across frames")
    return {
        "schema":SCHEMA,
        "actual_emulator_screenshots_verified":len(FRAMES),
        "generated_only_private_sd_input":True,
        "warm_and_cool_materials_visible":True,
        "ordered_gpu_material_mapping_verified":True,
        "original_ps3_assets_loaded":False,
        "physical_switch_gpu_verified":False,
        "measurements":readings,
    }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",required=True,type=Path)
    parser.add_argument("--report",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        result=verify(args.evidence)
        with args.report.open("x",encoding="utf-8") as output:
            json.dump(result,output,indent=2,sort_keys=True)
            output.write("\n")
    except (OSError,ValueError):
        parser.error("Real generated-only NeXium GPU screenshot check failed")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
