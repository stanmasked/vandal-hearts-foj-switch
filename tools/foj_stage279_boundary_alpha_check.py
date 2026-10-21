#!/usr/bin/env python3
"""Stage279: profile actual GPU transparency edges without guessing sampler mode.

Only a real NeXium CI capture establishes guest provenance. PIL-created
mock images test this classifier only, never actual GPU functionality.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image,ImageChops

from tools.foj_stage279_boundary_alpha_sd import (
    CASES,PROBES,PROFILE_X,PROFILE_Y,SCHEMA,SPLIT_X,WIDTH,near_atlas,
    expected_at,target_rgb,
)
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
from tools.foj_stage267_gpu_three_layer_check import BACKGROUNDS
from tools.foj_stage274_pass_contract_check import expected_receipt

ENDPOINT_TOLERANCE=8
ENDPOINT_MIN_MATCH=75
REFERENCE_CLEAR=target_rgb(0)
REFERENCE_OPAQUE=target_rgb(255)
DELTA=tuple(REFERENCE_OPAQUE[i]-REFERENCE_CLEAR[i] for i in range(3))
DENOM=sum(q*q for q in DELTA)
assert DENOM>0


def file_bytes(path:Path)->bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or linked Stage279 artifact: {path.name}")
    return path.read_bytes()


def normalized_opacity(pixel:tuple[int,int,int])->float:
    # Project the three-channel framebuffer onto the physically expected
    # straight-alpha vector, not any single 8-bit channel.
    return sum((pixel[i]-REFERENCE_CLEAR[i])*DELTA[i]
               for i in range(3))/DENOM


def inspect(path:Path,case:str)->dict:
    if case not in CASES:
        raise ValueError("Unexpected Stage279 boundary case")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage279 real GPU capture missing or linked")
    with Image.open(path) as im:
        rgb=im.convert("RGB")
    if rgb.size!=(1280,720):
        raise ValueError("Stage279 incorrect guest framebuffer dimensions")
    readings={}
    for name,(cx,cy) in PROBES.items():
        expected=expected_at(case,name)
        matched=sum(all(abs(rgb.getpixel((x,y))[i]-expected[i])
                        <=ENDPOINT_TOLERANCE for i in range(3))
                    for y in range(cy-4,cy+5)
                    for x in range(cx-4,cx+5))
        if matched<ENDPOINT_MIN_MATCH:
            raise ValueError(f"Stage279 {case} {name}: invalid endpoint RGB")
        readings[name]={"expected_rgb":list(expected),
                        "center_rgb":list(rgb.getpixel((cx,cy))),
                        "matching_pixels":matched}
    samples=[rgb.getpixel((x,PROFILE_Y)) for x in PROFILE_X]
    opacity=[normalized_opacity(pixel) for pixel in samples]
    ascending=case=="boundary-clear-left"
    oriented=(opacity if ascending else [1-p for p in opacity])
    if not (oriented[0]<0.12 and oriented[-1]>0.88):
        raise ValueError("Stage279 boundary endpoint opacity not exchanged")
    # Reject a fake black/off-color stripe and physically implausible
    # oscillations while allowing either nearest OR linear sampling.
    for rgb_val,level in zip(samples,opacity):
        if not -.07<=level<=1.07:
            raise ValueError("Stage279 out-of-envelope alpha sample")
        ideal=tuple(REFERENCE_CLEAR[i]+level*DELTA[i] for i in range(3))
        if any(abs(rgb_val[i]-ideal[i])>8 for i in range(3)):
            raise ValueError("Stage279 boundary sample not on source-over curve")
    if any(oriented[i+1]+.06<oriented[i]
           for i in range(len(oriented)-1)):
        raise ValueError("Stage279 nonmonotone alpha transition")
    if any(abs(oriented[i+1]-oriented[i])>.90
           for i in range(len(oriented)-1)):
        # A 0→255 nearest-filtered step can legitimately be >0.90!
        # Do not reject an abrupt native sample; just report it.
        pass
    crossing=[x for x,v in zip(PROFILE_X,oriented) if v>=.5]
    if not crossing or not 654<=crossing[0]<=667:
        raise ValueError("Stage279 GPU alpha boundary at unexpected pixel")
    mid=[x for x,v in zip(PROFILE_X,oriented) if .1<v<.9]
    if mid and (min(mid)<652 or max(mid)>669):
        raise ValueError("Stage279 implausibly wide blended boundary")
    return {
        "controls":readings,
        "profile_x":list(PROFILE_X),
        "profile_y":PROFILE_Y,
        "profile_rgb":[list(p) for p in samples],
        "estimated_opacity":[round(v,4) for v in opacity],
        "half_transition_x":crossing[0],
        "intermediate_sample_count":len(mid),
        "sampler_filter_mode":"NOT_INFERRED",
    }


def verify(root:Path)->dict:
    root=Path(root)
    results={}
    for case in CASES:
        folder=root/case
        manifest=json.loads(file_bytes(folder/"generated-input.json"))
        current=near_atlas(case)
        reference=generated_dds((*VIOLET,128))
        digest=hashlib.sha256(current).hexdigest()
        pristine_digest=hashlib.sha256(reference).hexdigest()
        if (manifest.get("schema")!=SCHEMA or
            manifest.get("scenario")!=case or
            manifest.get("generated_only") is not True or
            manifest.get("original_ps3_resources") is not False or
            manifest.get("actual_gpu_render_verified") is not False or
            manifest.get("changed_file")!="material0.dds" or
            manifest.get("near_original_dds_sha256")!=pristine_digest or
            manifest.get("near_dds_sha256")!=digest or
            manifest.get("near_alpha_split_x")!=SPLIT_X or
            manifest.get("near_texture_dimensions")!=[WIDTH,WIDTH] or
            manifest.get("profile_x_positions")!=list(PROFILE_X) or
            manifest.get("profile_y")!=PROFILE_Y or
            manifest.get("profile_goal")!=
                "measure transition monotonicity, not assert filter mode" or
            manifest.get("expected_native_pass_order")!=[2,1,0] or
            manifest.get("expected_probe_rgb")!={
                k:list(expected_at(case,k)) for k in PROBES}):
            raise ValueError("Stage279 source DDS provenance mismatch")
        for phase in ("before","after"):
            if file_bytes(folder/f"near-dds-{phase}.sha256")!=(
                    digest+"\n").encode("ascii"):
                raise ValueError("Stage279 source DDS identity changed")
        if file_bytes(folder/"native-sort-pass.txt")!=(
                b"FOJ_NATIVE_SORT_V1 2,1,0\n") or (
            file_bytes(folder/"native-alpha-pass.txt")!=
                expected_receipt("original")):
            raise ValueError("Stage279 native GPU descriptor witness invalid")
        file_bytes(folder/"guest.log")
        for marker in ("native-rear-alpha-reject.txt",
                       "native-topology-reject.txt"):
            forbidden=folder/marker
            if forbidden.exists() or forbidden.is_symlink():
                raise ValueError("Stage279 contradictory native refusal")
        first=inspect(folder/"gpu-initial.png",case)
        later=inspect(folder/"gpu-later.png",case)
        with Image.open(folder/"gpu-initial.png") as a,Image.open(
                folder/"gpu-later.png") as b:
            im1,im2=a.convert("RGB"),b.convert("RGB")
        if ImageChops.difference(im1,im2).getbbox() is None:
            raise ValueError("Stage279 duplicate framebuffer captures")
        if sum(im1.getpixel(p)!=im2.getpixel(p) for p in BACKGROUNDS)<3:
            raise ValueError("Stage279 unchanged GPU clear-color phase")
        if first["profile_rgb"]!=later["profile_rgb"]:
            raise ValueError("Stage279 material profile changed across frames")
        results[case]={"initial":first,"later":later}
    if results[CASES[0]]["initial"]["profile_rgb"]==(
            results[CASES[1]]["initial"]["profile_rgb"]):
        raise ValueError("Stage279 inverted alpha profiles indistinguishable")
    return {
        "schema":"foj.stage279.real_native_alpha_edge_profile.v1",
        "generated_only":True,
        "original_ps3_resources":False,
        "real_guest_frames_required":4,
        "native_pass_receipts_checked":True,
        "sampling_mode_assumed":False,
        "physical_switch_verified":False,
        "cases":results,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        result=verify(args.evidence)
        with args.report.open("x",encoding="utf-8") as handle:
            json.dump(result,handle,indent=2,sort_keys=True)
            handle.write("\n")
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print("Stage279 boundary audit refused: "+str(exc),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
