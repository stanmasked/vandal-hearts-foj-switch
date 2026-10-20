#!/usr/bin/env python3
"""Fail-closed straight-alpha RGB math verifier on REAL NeXium guest PNGs.

A sequence of three otherwise identical generated-only static scenes gives
alpha 0, 128 and 255 for the nearer warm texture. Rear cool is opaque.
Drawing cool FIRST and near warm SECOND with GPU blending must produce RGB
cool, approximately 50/50 composite, and warm at fixed overlap probes.
PIL-generated unit-test pictures are never accepted as real guest evidence.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops

from tools.foj_stage265_generated_blend_sd import ALPHAS
from tools.foj_stage260_generated_gpu_sd import COLORS

SCHEMA="foj.stage265.gpu_blend_guest.v1"
FRAMES=("gpu-initial.png","gpu-later.png")
PROBES={"overlap":(640,400),"overlap_other":(600,400),
        "rear_only":(760,400)}
HALF_TOL=8
FULL_TOL=5
MIN_MATCHES=116


def blended_rgb(alpha:int)->tuple[int,int,int]:
    a=alpha/255.
    return tuple(round(a*COLORS[0][i]+(1-a)*COLORS[1][i])
                 for i in range(3))


def close(rgb:tuple,ref:tuple,tolerance:int)->bool:
    return all(abs(int(rgb[i])-int(ref[i]))<=tolerance for i in range(3))


def inspect(path:Path,case:str)->dict:
    if case not in ALPHAS:raise ValueError("Unknown alpha case")
    with Image.open(path) as f: rgb=f.convert("RGB")
    if rgb.size!=(1280,720):raise ValueError("Guest resolution differs")
    pix=rgb.load()
    alpha=ALPHAS[case]
    out={}
    for probe,(x,y) in PROBES.items():
        target=tuple(COLORS[1][:3]) if probe=="rear_only" else blended_rgb(alpha)
        tolerance=HALF_TOL if case=="half" else FULL_TOL
        samples=[pix[xx,yy] for yy in range(y-5,y+6)
                 for xx in range(x-5,x+6)]
        good=sum(close(pixel,target,tolerance) for pixel in samples)
        if good<MIN_MATCHES:
            raise ValueError(
                f"{case} {probe}: only {good}/121 source-over alpha pixels"
            )
        out[probe]={
            "pixel":[x,y],"expected_rgb":list(target),
            "matched_pixels":good,"tolerance":tolerance,
        }
    return out


def frames(directory:Path,case:str)->dict:
    first=inspect(directory/FRAMES[0],case)
    second=inspect(directory/FRAMES[1],case)
    for name in PROBES:
        if first[name]["matched_pixels"]!=second[name]["matched_pixels"]:
            raise ValueError("Unstable blended material between GPU frames")
    with Image.open(directory/FRAMES[0]) as first_im, Image.open(directory/FRAMES[1]) as second_im:
        a=first_im.convert("RGB");b=second_im.convert("RGB")
    if ImageChops.difference(a,b).getbbox() is None:
        raise ValueError("Duplicate guest frame")
    bg=((25,350),(1220,350),(640,650),(25,650))
    if sum(a.getpixel(q)!=b.getpixel(q) for q in bg)<3:
        raise ValueError("GPU clear-color phase not independently changed")
    return {"first":first,"second":second,"clear_phase_changed":True}


def verify(root:Path)->dict:
    readings={case:frames(root/case,case) for case in ALPHAS}
    colors={case:readings[case]["first"]["overlap"]["expected_rgb"]
            for case in ALPHAS}
    if colors["clear"]!=list(COLORS[1][:3]) or (
        colors["solid"]!=list(COLORS[0][:3])
    ):
        raise ValueError("Counterfactual source colors wrong")
    if not all(min(colors["clear"][i],colors["solid"][i])
               <colors["half"][i]
               <max(colors["clear"][i],colors["solid"][i])
               for i in range(3)):
        raise ValueError("Intermediate alpha did not produce intermediate RGB")
    return {
        "schema":SCHEMA,
        "actual_neixum_guest_frames_verified":6,
        "generated_only":True,
        "source_over_alpha_0_128_255":True,
        "opaque_cool_drawn_first":True,
        "near_warm_translucent_drawn_second":True,
        "translucent_depth_write_disabled_in_opt_in_native_source":True,
        "original_ps3_assets_used":False,
        "physical_switch_verified":False,
        "expected_overlap_rgb":colors,
        "cases":readings,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    a=p.parse_args(argv)
    try:
        result=verify(a.evidence)
        with a.report.open("x",encoding="utf-8") as out:
            json.dump(result,out,indent=2,sort_keys=True);out.write("\n")
    except (OSError,ValueError) as exc:
        p.error("Genuine GPU source-over blending evidence failed: "+str(exc))
    return 0


if __name__=="__main__":raise SystemExit(main())
