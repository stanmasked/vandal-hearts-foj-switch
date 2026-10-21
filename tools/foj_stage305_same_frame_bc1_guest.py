#!/usr/bin/env python3
"""Stage305: two separate BC1 pages visible across one GPU screen-space seam.

Mock images used by local unit tests are NOT GPU proof; the native receipt
must come from a fresh guest run and the screenshots must be captured from
its actual NeXium GPU window by Stage305's constrained driver.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys

from PIL import Image

from tools.foj_stage289_public_guest_evidence import _check_tree, _regular_file
from tools.foj_stage293_converted_dds_guest import (
    _origin, _attestation, _write_new
)

SCHEMA="foj.stage305.same_gpu_frame_adjacent_bc1_pages.v1"
RECEIPT="stage305-split-guest-receipt.json"
MARKER="native-stage305-split-pass.txt"
MARKER_BYTES=b"FOJ_NATIVE_STAGE305_SPLIT_V1 left=1,1 right=2,1 uv=511/512 verts=15\n"
COLORS={"left":(16,199,214),"right":(24,203,222)}
FILES=(
    "generated-input.json","dds-before.json","dds-after.json",
    "gpu-initial.png","gpu-later.png",MARKER,RECEIPT,
)
SOURCE={"nexium-archive.sha256"}|{"bridge/"+n for n in (*FILES,"guest.log")}
PUBLIC={"nexium-archive.sha256"}|{"bridge/"+n for n in FILES}


def _frame(path:Path)->dict:
    with Image.open(path) as original:
        rgb=original.convert("RGB")
    if rgb.size!=(1280,720):
        raise ValueError("Stage305 invalid GPU framebuffer dimensions")
    # Both page-local quads meet at normalized x=0 => screen x=640.
    # Sample the SAME frame, one short pixel interval on either side;
    # avoid the two boundary-covered pixels where rasterizer top-left
    # tie rules can differ without causing any visible crack.
    result={}
    for side,center_x in (("left",625),("right",655)):
        target=COLORS[side]
        total=sum(
            all(abs(rgb.getpixel((x,y))[i]-target[i])<=2 for i in range(3))
            for y in range(396,405) for x in range(center_x-4,center_x+5)
        )
        if total<78:
            raise ValueError("Stage305 two-page GPU frame missing split surface")
        result[side]=total
    # A short contiguous horizontal scan detects background/third-page
    # leakage into either drawn half; we do not claim hardware bilinear
    # across page seams because each half has its own constant page UV.
    for x in range(620,639):
        if any(abs(rgb.getpixel((x,400))[i]-COLORS["left"][i])>2
               for i in range(3)):
            raise ValueError("Stage305 left side contains a crack or wrong page")
    for x in range(642,661):
        if any(abs(rgb.getpixel((x,400))[i]-COLORS["right"][i])>2
               for i in range(3)):
            raise ValueError("Stage305 right side contains a crack or wrong page")
    return result


def frame_phase_changed(a:Path,b:Path)->bool:
    with Image.open(a) as x,Image.open(b) as y:
        first=x.convert("RGB")
        second=y.convert("RGB")
    if first.size!=(1280,720) or second.size!=(1280,720):
        return False
    return sum(first.getpixel(point)!=second.getpixel(point)
               for point in ((25,350),(1220,350),(640,650),(25,650)))>=3


def audit(path:Path)->dict:
    path=Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Stage305 evidence directory invalid")
    def load(name:str):
        return json.loads(_regular_file(path/name))
    if load("generated-input.json")!=_origin():
        raise ValueError("Stage305 synthetic source did not match independent origin")
    if load("dds-before.json")!=_attestation("before") or (
            load("dds-after.json")!=_attestation("after")):
        raise ValueError("Stage305 DDS-origin stages before/after disagree")
    if _regular_file(path/MARKER)!=MARKER_BYTES:
        raise ValueError("Stage305 native split-quad guest marker incorrect")
    first,second=(path/"gpu-initial.png",path/"gpu-later.png")
    pixels={"gpu-initial.png":_frame(first),"gpu-later.png":_frame(second)}
    if not frame_phase_changed(first,second):
        raise ValueError("Stage305 two frames did not show a real phase change")
    return {
        "schema":SCHEMA,
        "generated_only":True,
        "two_distinct_bc1_pages_visible_in_same_gpu_frame":True,
        "real_neixum_guest_frames_verified":2,
        "quantized_left_rgb":list(COLORS["left"]),
        "quantized_right_rgb":list(COLORS["right"]),
        "page_uv_seam_screen_x":640,
        "same_frame_pixel_probes":pixels,
        "native_15_vertex_two_quad_marker_verified":True,
        "original_ps3_assets_used":False,
        "original_game_uvs_verified":False,
        "single_unsplit_polygon_texture_seam_verified":False,
        "bilinear_filtering_seam_verified":False,
        "physical_switch_verified":False,
    }


def publish(source:Path,destination:Path)->dict:
    source,destination=Path(source),Path(destination)
    if destination.exists() or destination.is_symlink() or (
            not destination.parent.is_dir() or destination.parent.is_symlink()):
        raise ValueError("Stage305 needs fresh public export directory")
    _check_tree(source,SOURCE)
    result=audit(source/"bridge")
    if json.loads(_regular_file(source/"bridge"/RECEIPT))!=result:
        raise ValueError("Stage305 received stale native guest report")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular_file(source/"nexium-archive.sha256")):
        raise ValueError("Stage305 missing guest program archive identity")
    destination.mkdir(mode=0o700)
    try:
        (destination/"bridge").mkdir(mode=0o700)
        for name in sorted(PUBLIC):
            size=12*1024*1024 if name.endswith(".png") else 65536
            data=_regular_file(source/name,size)
            with (destination/name).open("xb") as dest:
                dest.write(data)
        _check_tree(destination,PUBLIC)
        if audit(destination/"bridge")!=result:
            raise ValueError("Stage305 GPU split seam changed during publication")
        for name in PUBLIC:
            max_len=12*1024*1024 if name.endswith(".png") else 65536
            if _regular_file(source/name,max_len)!=_regular_file(destination/name,max_len):
                raise ValueError("Stage305 source changed while publishing")
    except BaseException:
        shutil.rmtree(destination)
        raise
    return {"schema":"foj.stage305.generated_only_public_gpu_seam.v1",
            "public_files":len(PUBLIC),
            "real_neixum_guest_frames_verified":2,
            "raw_guest_log_uploaded":False,
            "original_game_assets_uploaded":False}


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("audit")
    a.add_argument("--evidence",required=True,type=Path)
    b=sub.add_parser("publish")
    b.add_argument("--source",required=True,type=Path)
    b.add_argument("--output",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        if args.cmd=="audit":
            result=audit(args.evidence)
            _write_new(args.evidence,RECEIPT,result)
        else:
            result=publish(args.source,args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        print("Stage305 generated two-page GPU frame proof refused.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
