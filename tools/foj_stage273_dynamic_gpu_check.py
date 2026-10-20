#!/usr/bin/env python3
"""Verify real GPU frames from dynamically sorted Z-swapped synthetic scenes.

Only the NeXium CI runner supplies actual framebuffer provenance.
Constructed PIL images in host tests never constitute GPU evidence.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from PIL import Image,ImageChops

from tools.foj_stage273_dynamic_gpu_sd import CASES,expected_rgb,BACK_TO_FRONT
from tools.foj_stage266_transparency_order import COOL
from tools.foj_stage267_gpu_three_layer_check import PROBES,BACKGROUNDS

SCHEMA="foj.stage273.dynamic_gpu_guest.v1"
TOLERANCE=8
MIN_CORRECT=116


def inspect(path:Path,case:str)->dict:
    if case not in CASES:
        raise ValueError("Unknown Z-sort case")
    with Image.open(path) as frame:
        rgb=frame.convert("RGB")
    if rgb.size!=(1280,720):
        raise ValueError("Wrong NeXium frame dimensions")
    samples={}
    pixels=rgb.load()
    for name,(x,y) in PROBES.items():
        expected=COOL if name=="rear_only" else expected_rgb(case)
        matched=sum(all(abs(pixels[xx,yy][i]-expected[i])<=TOLERANCE
                        for i in range(3))
                    for yy in range(y-5,y+6)
                    for xx in range(x-5,x+6))
        if matched<MIN_CORRECT:
            raise ValueError(f"{case}: {name}: {matched}/121 correct RGBA output")
        samples[name]={
            "pixel":[x,y],
            "expected_rgb":list(expected),
            "matching_pixels":matched,
            "tolerance":TOLERANCE,
        }
    return samples


def verify(root:Path)->dict:
    seen={}
    signatures=[]
    for case in CASES:
        folder=root/case
        source=folder/"generated-input.json"
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing generated-only receipt for {case}")
        r=json.loads(source.read_text(encoding="utf-8"))
        if (r.get("schema")!="foj.stage273.dynamic_gpu_sort.v1"
            or r.get("scenario")!=case
            or r.get("generated_only") is not True
            or r.get("guest_proof_claimed") is not False
            or r.get("expected_native_pass_order")!=list(BACK_TO_FRONT[case])
            or r.get("expected_overlap_rgb")!=list(expected_rgb(case))):
            raise ValueError(f"Untrusted generated scene receipt for {case}")
        first=folder/"gpu-initial.png"
        later=folder/"gpu-later.png"
        a=inspect(first,case)
        b=inspect(later,case)
        with Image.open(first) as before,Image.open(later) as after:
            x=before.convert("RGB")
            y=after.convert("RGB")
        if ImageChops.difference(x,y).getbbox() is None:
            raise ValueError("Duplicate frames are not guest evidence")
        if sum(x.getpixel(p)!=y.getpixel(p) for p in BACKGROUNDS)<3:
            raise ValueError("GPU clear-color phase did not change")
        if [a[n]["matching_pixels"] for n in PROBES]!=[
              b[n]["matching_pixels"] for n in PROBES]:
            raise ValueError("Material footprints changed across frames")
        signatures.append(tuple(x.getpixel(PROBES["overlap"])))
        seen[case]={
            "first":a,"later":b,
            "expected_draw_order":list(BACK_TO_FRONT[case]),
            "background_phase_changed":True,
        }
    if len(set(signatures))!=len(CASES):
        raise ValueError("Reversed translucent layers did not change output")
    return {
        "schema":SCHEMA,
        "verified_guest_frames":2*len(CASES),
        "actual_guest_provenance":"requires real NeXium GitHub Actions workflow",
        "generated_only":True,
        "original_ps3_assets":False,
        "physical_switch_verified":False,
        "cases":seen,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        summary=verify(args.evidence)
        with args.report.open("x",encoding="utf-8") as handle:
            json.dump(summary,handle,indent=2,sort_keys=True)
            handle.write("\n")
    except (OSError,ValueError) as exc:
        print("Stage273 GPU order proof rejected: "+str(exc),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
