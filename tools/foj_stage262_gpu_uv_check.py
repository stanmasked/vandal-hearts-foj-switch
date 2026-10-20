#!/usr/bin/env python3
"""Read actual NeXium RGB screenshots and prove two independent DDS UV maps.

Expected positions come from the documented camera, the independent Stage260
triangle fixture, and barycentric inversion of known UVs. We do not fit or
shift the predicted coordinates to match colored pixels. The test refuses
swapped atlases, flipped V, mirrored U, flat material colors, missing pixels,
wrong quadrant order, and duplicate guest screenshots.

Generated-only data; original Vandal Hearts artwork is never loaded.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops

from tools.foj_stage261_projection_audit import (
    TRIANGLES, projected_vertices
)
from tools.foj_stage262_generated_uv_sd import PALETTES, QUADRANTS

SCHEMA="foj.stage262.gpu_uv_guest.v1"
FRAMES=("gpu-initial.png","gpu-later.png")
UV_SITES=(
    (.40,.40),(.60,.40),(.25,.75),(.75,.75)
)
COLOR_TOLERANCE=24
MIN_LOCAL_MATCHES=32
MIN_QUADRANT_SAMPLES=220


def close(a:tuple,b:tuple)->bool:
    return all(abs(int(a[i])-int(b[i]))<=COLOR_TOLERANCE
               for i in range(3))


def screen_for_uv(uv:tuple,xy:tuple)->tuple:
    # UV(A)=(0,1), UV(B)=(1,1), UV(C)=(.5,0).
    u,v=uv
    if not 0<=u<=1 or not 0<=v<=1:
        raise ValueError("Invalid UV site")
    apex=1.-v
    right=u-.5*apex
    left=v-right
    if min(apex,right,left)<-1e-6:
        raise ValueError("UV sample outside triangular atlas")
    x=round(left*xy[0][0]+right*xy[1][0]+apex*xy[2][0])
    y=round(left*xy[0][1]+right*xy[1][1]+apex*xy[2][1])
    return int(x),int(y)


def inspect(path:Path)->dict:
    with Image.open(path) as image:
        frame=image.convert("RGB")
    if frame.size!=(1280,720):
        raise ValueError("Unexpected NeXium capture resolution")
    pixel=frame.load()
    readings={}
    for material in ("warm","cool"):
        xy=projected_vertices(1280,720,TRIANGLES[material])
        colorlist=PALETTES[material]
        other=PALETTES["cool" if material=="warm" else "warm"]
        xs,ys=zip(*xy)
        region=(max(0,min(xs)-12),max(0,min(ys)-15),
                min(1280,max(xs)+13),min(720,max(ys)+16))
        counts=[0,0,0,0]
        wrong=0
        for y in range(region[1],region[3],2):
            for x in range(region[0],region[2],2):
                col=pixel[x,y]
                matched=[idx for idx,color in enumerate(colorlist)
                         if close(col,color)]
                if matched:
                    # Our chosen palette quadrants never overlap within tolerance.
                    if len(matched)!=1:
                        raise ValueError("Ambiguous quadrant palette")
                    counts[matched[0]]+=1
                elif any(close(col,c) for c in other):
                    wrong+=1
        if any(count<MIN_QUADRANT_SAMPLES for count in counts):
            raise ValueError("Missing one of four material atlas quadrants: "+
                             material)
        if wrong>50:
            raise ValueError("Other material intrudes into triangle: "+material)
        local={}
        for idx,uv in enumerate(UV_SITES):
            x,y=screen_for_uv(uv,xy)
            expected=colorlist[idx]
            matching=sum(close(pixel[xx,yy],expected)
                         for yy in range(y-8,y+9,2)
                         for xx in range(x-8,x+9,2))
            if matching<MIN_LOCAL_MATCHES:
                raise ValueError(
                    "UV quadrant orientation/interpolation mismatch at "+
                    material+" "+QUADRANTS[idx]
                )
            local[QUADRANTS[idx]]={
                "uv":[uv[0],uv[1]],
                "independent_pixel":[x,y],
                "matching_samples":matching,
            }
        readings[material]={
            "color_quadrant_samples":dict(zip(QUADRANTS,counts)),
            "interpolated_uv_samples":local,
            "other_material_pixels":wrong,
        }
    return readings


def audit(evidence:Path)->dict:
    first=inspect(evidence/FRAMES[0])
    second=inspect(evidence/FRAMES[1])
    for material in first:
        for quad in QUADRANTS:
            a=first[material]["interpolated_uv_samples"][quad]
            b=second[material]["interpolated_uv_samples"][quad]
            if a["matching_samples"]<MIN_LOCAL_MATCHES or (
                abs(a["matching_samples"]-b["matching_samples"])>18
            ):
                raise ValueError("Unstable GPU UV colors between guest frames")
    with Image.open(evidence/FRAMES[0]) as im0,Image.open(evidence/FRAMES[1]) as im1:
        a,b=im0.convert("RGB"),im1.convert("RGB")
        if ImageChops.difference(a,b).getbbox() is None:
            raise ValueError("Duplicate screenshot cannot prove two GPU frames")
        if sum(a.getpixel(p)!=b.getpixel(p) for p in (
            (40,350),(1240,350),(640,600),(40,600)
        ))<3:
            raise ValueError("GPU background did not independently change")
    return {
        "schema":SCHEMA,
        "source":"real_neXium_gpu_window_captures_only",
        "generated_two_materials":True,
        "eight_distinct_uv_quadrants_verified":True,
        "confirmed_bilinear_or_nearest_uv_mapping_at_four_sites_per_material":True,
        "frame_count":2,
        "original_foj_assets_used":False,
        "physical_switch_verified":False,
        "first":first,"second":second,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        result=audit(args.evidence)
        with args.report.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2,sort_keys=True)
            f.write("\n")
    except (ValueError,OSError) as exc:
        p.error("Actual NeXium GPU UV quadrant validation failed: "+str(exc))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
