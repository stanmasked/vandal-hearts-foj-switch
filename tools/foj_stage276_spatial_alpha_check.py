#!/usr/bin/env python3
"""Stage276 independent classifier for real guest spatial DDS alpha.

Mock images test only classifier behavior. Only a completed CI NeXium
launch plus archived exact-head artifacts proves real GPU presentation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image,ImageChops
from tools.foj_stage276_spatial_alpha_sd import (
    CASES,PROBES,SCHEMA,SPLIT_X,WIDTH,
    expected_at,near_atlas,
)
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
from tools.foj_stage267_gpu_three_layer_check import BACKGROUNDS
from tools.foj_stage274_pass_contract_check import expected_receipt

TOLERANCE=8
MIN_CORRECT=75
EVIDENCE_SCHEMA="foj.stage276.real_spatial_alpha_gpu.v1"


def inspect(path:Path,case:str)->dict:
    if case not in CASES:
        raise ValueError("Unknown Stage276 spatial GPU case")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing real spatial-alpha capture")
    with Image.open(path) as image:
        rgb=image.convert("RGB")
    if rgb.size!=(1280,720):
        raise ValueError("Stage276 unexpected GPU image dimensions")
    result={}
    px=rgb.load()
    for name,(x,y) in PROBES.items():
        expected=expected_at(case,name)
        count=sum(all(abs(px[i,j][k]-expected[k])<=TOLERANCE
                      for k in range(3))
                  for j in range(y-4,y+5)
                  for i in range(x-4,x+5))
        if count<MIN_CORRECT:
            raise ValueError(
                f"{case} {name}: {count}/81 matched expected spatial alpha "
                f"RGB {expected}, actual center {px[x,y]}")
        result[name]={
            "center":list(px[x,y]),
            "expected_rgb":list(expected),
            "matching_pixels":count,
            "center_coordinates":[x,y],
        }
    return result


def require(path:Path)->bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or linked Stage276 input: {path.name}")
    return path.read_bytes()


def verify(root:Path)->dict:
    root=Path(root)
    receipts={}
    for case in CASES:
        folder=root/case
        meta=json.loads(require(folder/"generated-input.json"))
        pristine=generated_dds((*VIOLET,128))
        changed=near_atlas(case)
        old_hash=hashlib.sha256(pristine).hexdigest()
        new_hash=hashlib.sha256(changed).hexdigest()
        if (meta.get("schema")!=SCHEMA or meta.get("scenario")!=case or
            meta.get("generated_only") is not True or
            meta.get("original_ps3_resources") is not False or
            meta.get("actual_gpu_render_verified") is not False or
            meta.get("changed_file")!="material0.dds" or
            meta.get("near_original_dds_sha256")!=old_hash or
            meta.get("near_dds_sha256")!=new_hash or
            meta.get("near_alpha_split_x")!=SPLIT_X or
            meta.get("near_texture_dimensions")!=[WIDTH,WIDTH] or
            meta.get("expected_native_pass_order")!=[2,1,0] or
            meta.get("expected_probe_rgb")!={
                name:list(expected_at(case,name)) for name in PROBES}):
            raise ValueError("Stage276 generated DDS manifest mismatch")
        for phase in ("before","after"):
            witness=require(folder/f"near-dds-{phase}.sha256")
            if witness!=(new_hash+"\n").encode("ascii"):
                raise ValueError("Stage276 actual DDS changed or witness forged")
        if (require(folder/"native-sort-pass.txt")!=
                b"FOJ_NATIVE_SORT_V1 2,1,0\n" or
            require(folder/"native-alpha-pass.txt")!=
                expected_receipt("original")):
            raise ValueError("Stage276 inconsistent native pass-state receipts")
        require(folder/"guest.log")
        for forbidden in ("native-rear-alpha-reject.txt",
                          "native-topology-reject.txt"):
            x=folder/forbidden
            if x.is_symlink() or x.exists():
                raise ValueError("Stage276 positive GPU case contradicts refusal")
        first=folder/"gpu-initial.png"
        second=folder/"gpu-later.png"
        first_r=inspect(first,case)
        later_r=inspect(second,case)
        with Image.open(first) as a,Image.open(second) as b:
            im1,im2=a.convert("RGB"),b.convert("RGB")
        if ImageChops.difference(im1,im2).getbbox() is None:
            raise ValueError("Stage276 duplicate guest captures")
        if sum(im1.getpixel(pos)!=im2.getpixel(pos)
               for pos in BACKGROUNDS)<3:
            raise ValueError("Stage276 no independent GPU background phase")
        if any(first_r[k]["matching_pixels"]!=later_r[k]["matching_pixels"]
               for k in PROBES):
            raise ValueError("Stage276 material footprint changed with time")
        receipts[case]={"initial":first_r,"later":later_r}
    # A single uniform-alpha atlas could not pass: the same two probes
    # are expected to exchange their two distinct colors between cases.
    for name in ("left_overlap","right_overlap"):
        if expected_at(CASES[0],name)==expected_at(CASES[1],name):
            raise ValueError("Stage276 expected colors do not differ")
    return {
        "schema":EVIDENCE_SCHEMA,
        "scenes":list(CASES),
        "real_guest_rgb_frames_required":4,
        "native_sort_and_state_receipts_checked":True,
        "generated_only":True,
        "original_ps3_resources":False,
        "physical_switch_verified":False,
        "actual_guest_provenance":"requires real GitHub Actions NeXium guest",
        "cases":receipts,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        result=verify(args.evidence)
        with args.report.open("x",encoding="utf-8") as target:
            json.dump(result,target,indent=2,sort_keys=True)
            target.write("\n")
    except (OSError,ValueError,TypeError,KeyError) as e:
        print("Stage276 spatial-alpha guest evidence refused: "+str(e),
              file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
