#!/usr/bin/env python3
"""Stage306: eight patterned BC1 color bands visible across two pages on one GPU surface.

Mock images used by local unit tests are NOT GPU proof; the native receipt
must come from a fresh guest run and the screenshots must be captured from
its actual NeXium GPU window by Stage306's constrained driver.
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

SCHEMA="foj.stage306.interpolated_uv_eight_bc1_bands_on_gpu.v1"
RECEIPT="stage306-pattern-guest-receipt.json"
MARKER="native-stage306-pattern-pass.txt"
MARKER_BYTES=b"FOJ_NATIVE_STAGE306_PATTERN_V1 bands=4x2 pages=1,1+2,1 uv=interpolated verts=15\n"
COLORS={
    "left":((255,0,0),(255,130,0),(0,0,255),(0,255,255)),
    "right":((0,255,255),(255,0,255),(0,255,0),(255,255,0))
}
FILES=(
    "generated-input.json","dds-before.json","dds-after.json",
    "gpu-initial.png","gpu-later.png",MARKER,RECEIPT,
)
SOURCE={"nexium-archive.sha256"}|{"bridge/"+n for n in (*FILES,"guest.log")}
PUBLIC={"nexium-archive.sha256"}|{"bridge/"+n for n in FILES}


def _frame(path:Path)->dict:
    with Image.open(path) as original:
        image=original.convert("RGB")
    if image.size!=(1280,720):
        raise ValueError("Stage306 unexpected guest framebuffer size")
    # Each quad is 384 pixels wide. Native fragment shader must interpolate
    # page-local U across its four 64-texel BC1 bands. Sample all 8 band
    # interiors, not just one center pixel or the native CPU receipt.
    result={}
    for side,x0 in (("left",256),("right",640)):
        for band,target in enumerate(COLORS[side]):
            center=x0+48+band*96
            hit=sum(
                all(abs(image.getpixel((x,y))[i]-target[i])<=3
                    for i in range(3))
                for y in range(396,405)
                for x in range(center-4,center+5)
            )
            if hit<78:
                raise ValueError("Stage306 GPU UV interpolation/band color mismatch")
            result[f"{side}_{band}"]=hit
    # The cross-page seam uses the same CYAN BC1 blocks on both sides:
    # independently validate near-boundary pixels on each half.
    cyan=(0,255,255)
    for x in list(range(629,639))+list(range(642,652)):
        if any(abs(image.getpixel((x,400))[i]-cyan[i])>3 for i in range(3)):
            raise ValueError("Stage306 GPU page seam cracked or leaked a band")
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
        raise ValueError("Stage306 evidence directory invalid")
    def load(name:str):
        return json.loads(_regular_file(path/name))
    if load("generated-input.json")!=_origin():
        raise ValueError("Stage306 synthetic source did not match independent origin")
    if load("dds-before.json")!=_attestation("before") or (
            load("dds-after.json")!=_attestation("after")):
        raise ValueError("Stage306 DDS-origin stages before/after disagree")
    if _regular_file(path/MARKER)!=MARKER_BYTES:
        raise ValueError("Stage306 native split-quad guest marker incorrect")
    first,second=(path/"gpu-initial.png",path/"gpu-later.png")
    pixels={"gpu-initial.png":_frame(first),"gpu-later.png":_frame(second)}
    if not frame_phase_changed(first,second):
        raise ValueError("Stage306 two frames did not show a real phase change")
    return {
        "schema":SCHEMA,
        "generated_only":True,
        "two_patterned_bc1_pages_visible_in_same_gpu_frame":True,
        "interpolated_uv_bands_verified":8,
        "matching_page_edge_color_verified":True,
        "real_neixum_guest_frames_verified":2,
        "quantized_left_bands_rgb":[list(x) for x in COLORS["left"]],
        "quantized_right_bands_rgb":[list(x) for x in COLORS["right"]],
        "page_uv_seam_screen_x":640,
        "same_frame_pixel_probes":pixels,
        "native_15_vertex_interpolated_uv_marker_verified":True,
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
        raise ValueError("Stage306 needs fresh public export directory")
    _check_tree(source,SOURCE)
    result=audit(source/"bridge")
    if json.loads(_regular_file(source/"bridge"/RECEIPT))!=result:
        raise ValueError("Stage306 received stale native guest report")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular_file(source/"nexium-archive.sha256")):
        raise ValueError("Stage306 missing guest program archive identity")
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
            raise ValueError("Stage306 GPU split seam changed during publication")
        for name in PUBLIC:
            max_len=12*1024*1024 if name.endswith(".png") else 65536
            if _regular_file(source/name,max_len)!=_regular_file(destination/name,max_len):
                raise ValueError("Stage306 source changed while publishing")
    except BaseException:
        shutil.rmtree(destination)
        raise
    return {"schema":"foj.stage306.generated_only_patterned_uv_gpu_evidence.v1",
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
        print("Stage306 generated two-page GPU frame proof refused.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
