#!/usr/bin/env python3
"""Stage304: audit two *actual* NeXium guest runs selecting neighbor BC1 pages.

Mock PNGs in unit tests never constitute GPU evidence. Real evidence is
independently collected by the Stage274 guest drive and native NRO receipts.
This parser exports only explicitly audited generated-only PNGs/JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys

from PIL import Image

from tools.foj_stage267_gpu_three_layer_check import PROBES
from tools.foj_stage289_public_guest_evidence import _check_tree, _regular_file
from tools.foj_stage293_converted_dds_guest import (
    _write_new, audit as stage293_audit
)

SCHEMA="foj.stage304.actual_guest_bc1_neighbor_uv.v1"
MARKER="native-stage304-seam-pass.txt"
RECEIPT="stage304-seam-guest-receipt.json"
GUEST_FRAMES=("gpu-initial.png","gpu-later.png")
COLORS={"left":(16,199,214),"right":(24,203,222)}
MARKERS={
    "left":b"FOJ_NATIVE_STAGE304_SEAM_V1 side=left p=1,1 lx=255 ly=128 rgb=16,199,214\n",
    "right":b"FOJ_NATIVE_STAGE304_SEAM_V1 side=right p=2,1 lx=0 ly=128 rgb=24,203,222\n",
}
PUBLIC=(
    "generated-input.json","dds-before.json","dds-after.json",
    *GUEST_FRAMES,"native-sort-pass.txt","native-alpha-pass.txt",
    MARKER,RECEIPT,
)
ARCHIVE="nexium-archive.sha256"
SOURCE={ARCHIVE}|{"bridge/"+n for n in (*PUBLIC,"guest.log")}
EXPORTED={ARCHIVE}|{"bridge/"+n for n in PUBLIC}
PROBE=PROBES["rear_only"]


def pixel_probe(path:Path,side:str)->int:
    if side not in COLORS:
        raise ValueError("Stage304 unknown native UV side")
    with Image.open(path) as img:
        image=img.convert("RGB")
    if image.size!=(1280,720):
        raise ValueError("Stage304 wrong real framebuffer size")
    cx,cy=PROBE
    expected=COLORS[side]
    matches=sum(all(abs(image.getpixel((x,y))[k]-expected[k])<=2
                    for k in range(3))
                for y in range(cy-5,cy+6)
                for x in range(cx-5,cx+6))
    if matches<116:
        raise ValueError("Stage304 wrong BC1 neighbor page on actual GPU")
    return matches


def audit(evidence:Path,side:str)->dict:
    if side not in COLORS:
        raise ValueError("Stage304 unknown side")
    evidence=Path(evidence)
    if evidence.is_symlink() or not evidence.is_dir():
        raise ValueError("Stage304 evidence location unsafe")
    checked=stage293_audit(evidence)
    if checked["guest_frames_verified"]!=2 or not checked["generated_only"]:
        raise ValueError("Stage304 Stage293 original generated-source gate changed")
    if _regular_file(evidence/MARKER)!=MARKERS[side]:
        raise ValueError("Stage304 native GPU side witness did not match")
    readings={name:pixel_probe(evidence/name,side) for name in GUEST_FRAMES}
    return {
        "schema":SCHEMA,
        "side":side,
        "selected_page":{"x":1 if side=="left" else 2,"y":1},
        "selected_uv_texel":{"x":511 if side=="left" else 512,"y":384},
        "local_x":255 if side=="left" else 0,
        "expected_nearest_page_rgb":list(COLORS[side]),
        "gpu_probe_matches":readings,
        "real_neixum_guest_frames_verified":2,
        "guest_native_side_and_uv_receipt_verified":True,
        "source_generated_in_native_c":True,
        "actual_stage301_bc1_decode_and_stage303_uv_router_in_guest":True,
        "generated_only":True,
        "original_ps3_assets_used":False,
        "original_game_uv_materials_verified":False,
        "physical_switch_verified":False,
        "single_triangle_across_seam_gpu_tested":False,
        "bilinear_atlas_seams_tested":False,
    }


def publish(source:Path,output:Path,side:str)->dict:
    source,output=Path(source),Path(output)
    if (output.exists() or output.is_symlink() or
            not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage304 public folder must be fresh")
    _check_tree(source,SOURCE)
    report=audit(source/"bridge",side)
    saved=json.loads(_regular_file(source/"bridge"/RECEIPT))
    if report!=saved:
        raise ValueError("Stage304 guest report differs from independently checked result")
    checksum=_regular_file(source/ARCHIVE)
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",checksum):
        raise ValueError("Stage304 missing NeXium archive identity")
    output.mkdir(mode=0o700)
    try:
        (output/"bridge").mkdir(mode=0o700)
        for relative in sorted(EXPORTED):
            src=source/relative
            limit=12*1024*1024 if src.name in GUEST_FRAMES else 65536
            body=_regular_file(src,limit)
            with (output/relative).open("xb") as stream:
                stream.write(body)
        _check_tree(output,EXPORTED)
        if audit(output/"bridge",side)!=report:
            raise ValueError("Stage304 exported frames no longer prove page selection")
        for relative in EXPORTED:
            name=Path(relative).name
            limit=12*1024*1024 if name in GUEST_FRAMES else 65536
            if _regular_file(source/relative,limit)!=_regular_file(output/relative,limit):
                raise ValueError("Stage304 original guest proof changed during publication")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema":"foj.stage304.strict_generated_uv_evidence_publication.v1",
        "side":side,
        "generated_only":True,
        "public_files":len(EXPORTED),
        "raw_guest_logs_uploaded":False,
        "source_game_assets_uploaded":False,
        "real_guest_frames_verified":2,
    }


def pair(left:Path,right:Path)->dict:
    def one(folder:Path,side:str)->dict:
        folder=Path(folder)
        _check_tree(folder,EXPORTED)
        result=audit(folder/"bridge",side)
        saved=json.loads(_regular_file(folder/"bridge"/RECEIPT))
        if saved!=result:
            raise ValueError("Stage304 paired receipt mismatch")
        return result
    l,r=one(left,"left"),one(right,"right")
    from PIL import ImageChops
    for name in GUEST_FRAMES:
        with Image.open(left/"bridge"/name) as a,Image.open(right/"bridge"/name) as b:
            if ImageChops.difference(a.convert("RGB"),b.convert("RGB")).getbbox() is None:
                raise ValueError("Stage304 both neighbor sides produced identical GPU frames")
        if pixel_probe(left/"bridge"/name,"right")>=116 or (
                pixel_probe(right/"bridge"/name,"left")>=116):
            raise ValueError("Stage304 opposite UV side accepted same framebuffer")
    return {
        "schema":"foj.stage304.two_actual_neixum_neighbor_pages_verified.v1",
        "case_count":2,"total_real_guest_frames":4,
        "left_uv_page":[1,1],"right_uv_page":[2,1],
        "adjacent_atlas_texel_boundary":[511,512],
        "actual_native_bc1_uv_source_to_gpu_verified":True,
        "generated_only":True,
        "original_ps3_assets":False,
        "native_single_triangle_seam_or_bilinear_not_verified":True,
    }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    a=sub.add_parser("audit")
    a.add_argument("--side",required=True,choices=COLORS)
    a.add_argument("--evidence",required=True,type=Path)
    b=sub.add_parser("publish")
    b.add_argument("--side",required=True,choices=COLORS)
    b.add_argument("--source",required=True,type=Path)
    b.add_argument("--output",required=True,type=Path)
    c=sub.add_parser("pair")
    c.add_argument("--left",required=True,type=Path)
    c.add_argument("--right",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        if args.action=="audit":
            result=audit(args.evidence,args.side)
            _write_new(args.evidence,RECEIPT,result)
        elif args.action=="publish":
            result=publish(args.source,args.output,args.side)
        else:
            result=pair(args.left,args.right)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        print("Stage304 independent generated BC1 UV guest evidence refused.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
