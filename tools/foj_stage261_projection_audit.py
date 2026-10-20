#!/usr/bin/env python3
"""Stage261: compare ACTUAL generated NeXium GPU polygons with CPU projection.

Do not infer source provenance from pixels. Evidence must be acquired by the
independent Stage260 guest workflow (which creates the PNGs at runtime).
Independent predicted triangle coordinates come from the clean-room camera
contract, not from fitting a shape to the observed screenshots.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

SCHEMA="foj.stage261.generated_gpu_projection.v1"
STATES=("gpu-initial.png","gpu-later.png")
# Invented Stage260 FOJRM fixture vertices. This reference deliberately does
# not call the C GPU pipeline or dynamically fit polygons to screenshots.
TRIANGLES={
    "warm":((-.86,-.42),(-.03,-.42),(-.44,.64)),
    "cool":((.03,-.42),(.86,-.42),(.44,.64)),
}
MIN_IOU=.78
MIN_PRECISION=.90
MIN_RECALL=.81


def projected_vertices(width:int,height:int,vertices:tuple)->tuple:
    # Clean-room projection contract: center(0,0), extent=2, zoom=1,
    # yaw=pitch=0, scale=0.84*min(frame dimensions)/extent.
    if width!=1280 or height!=720:
        raise ValueError("Expected exact 1280x720 framebuffer for calibration")
    scale=.84*min(width,height)/2.
    return tuple((round(width/2+scale*x),round(height/2-scale*y))
                 for x,y in vertices)


def is_material(rgb:tuple,name:str)->bool:
    r,g,b=rgb
    if name=="warm":
        return r>160 and g<145 and b<130 and r>g+75
    if name=="cool":
        return r<130 and g>150 and b>145 and b>r+85 and g>r+80
    raise ValueError("Unknown material")


def inspect(path:Path)->dict:
    with Image.open(path) as loaded:
        frame=loaded.convert("RGB")
    width,height=frame.size
    if (width,height)!=(1280,720):
        raise ValueError("Actual screenshot size differs from camera contract")
    px=frame.load()
    findings={}
    for name,vertices in TRIANGLES.items():
        triangle=projected_vertices(width,height,vertices)
        mask=Image.new("1",(width,height),0)
        ImageDraw.Draw(mask).polygon(triangle,fill=1)
        mp=mask.load()
        xs,ys=zip(*triangle)
        left=max(0,min(xs)-25);right=min(width,max(xs)+26)
        top=max(0,min(ys)-25);bottom=min(height,max(ys)+26)
        observed=expected=intersection=0
        xmin=ymin=10**9
        xmax=ymax=-1
        for y in range(top,bottom):
            for x in range(left,right):
                actual=is_material(px[x,y],name)
                ref=bool(mp[x,y])
                observed+=actual
                expected+=ref
                intersection+=actual and ref
                if actual:
                    xmin=min(xmin,x);xmax=max(xmax,x)
                    ymin=min(ymin,y);ymax=max(ymax,y)
        if not observed or not expected:
            raise ValueError("GPU polygon missing or invalid prediction")
        union=observed+expected-intersection
        iou=intersection/union
        precision=intersection/observed
        recall=intersection/expected
        if (iou<MIN_IOU or precision<MIN_PRECISION or
            recall<MIN_RECALL):
            raise ValueError("GPU projection silhouette mismatch: "+name)
        if xmax-xmin<185 or ymax-ymin<245:
            raise ValueError("GPU polygon excessively narrow or flat: "+name)
        findings[name]={
            "predicted_vertices":[list(q) for q in triangle],
            "observed_bbox":[xmin,ymin,xmax,ymax],
            "pixel_count":observed,
            "reference_pixel_count":expected,
            "silhouette_iou":round(iou,4),
            "silhouette_precision":round(precision,4),
            "silhouette_recall":round(recall,4),
        }
    if findings["warm"]["observed_bbox"][2]>=findings["cool"]["observed_bbox"][2]:
        raise ValueError("Expected ordered warm-left/cool-right GPU batches")
    return findings


def audit(evidence:Path)->dict:
    first=inspect(evidence/STATES[0])
    second=inspect(evidence/STATES[1])
    for name in TRIANGLES:
        one,two=first[name],second[name]
        if one["observed_bbox"]!=two["observed_bbox"]:
            raise ValueError("GPU silhouette moved between static frames: "+name)
        if abs(one["silhouette_iou"]-two["silhouette_iou"])>.02:
            raise ValueError("GPU projection score unstable: "+name)
    with Image.open(evidence/STATES[0]) as im0, Image.open(evidence/STATES[1]) as im1:
        a,b=im0.convert("RGB"),im1.convert("RGB")
        if ImageChops.difference(a,b).getbbox() is None:
            raise ValueError("Duplicate static screenshot not independent guest frames")
        # The alternating GPU clear background must change away from triangles.
        changed=sum(a.getpixel(pt)!=b.getpixel(pt) for pt in (
            (640,360),(50,350),(1100,350),(640,600),(50,600)))
        if changed<3:
            raise ValueError("No visible alternating GPU clear background")
    return {
        "schema":SCHEMA,
        "source":"real_neXium_guest_pngs_generated_assets_only",
        "frame_count":2,
        "expected_resolution":[1280,720],
        "geometry_projection_checked":True,
        "material_slot_order_checked":True,
        "not_original_foj_assets":True,
        "not_physical_switch":True,
        "frame_a":first,"frame_b":second,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        result=audit(args.evidence)
        with args.report.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2,sort_keys=True)
            f.write("\n")
    except (ValueError,OSError):
        p.error("Real GPU triangle geometry did not match independent CPU projection")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
