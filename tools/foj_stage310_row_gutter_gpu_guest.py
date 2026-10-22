#!/usr/bin/env python3
"""Stage310 generated-only row-patterned BC1 seam evidence; real NeXium only.

An ordinary generated PNG cannot attest GPU behavior. Host mocks exercise
negative checks, while live guest frames + native marker + Stage293 DDS
before/after provenance are required for actual CI proof.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from PIL import Image
from tools.foj_stage289_public_guest_evidence import _check_tree,_regular_file
from tools.foj_stage293_converted_dds_guest import _origin,_attestation,_write_new
from tools.foj_stage309_gutter_gpu_guest import phase_changed

MARKER="native-stage310-row-gutter-pass.txt"
RECEIPT="stage310-row-gutter-guest-receipt.json"
MARKER_BYTES=(b"FOJ_NATIVE_STAGE310_ROW_GUTTER_V1 pairs=8 rows=256 "
              b"strict_mix=256 pages=1,1+2,1 verts=18\n")
BANDS565=(
    (0x001f,0xf800,0x07e0,0xffe0,0xf81f,0x07ff,0xffff,0x0000),
    (0xffe0,0x07e0,0x001f,0xf800,0x07ff,0xf81f,0x0000,0xffff)
)
def rgb565(v:int)->tuple[int,int,int]:
    r,g,b=(v>>11)&31,(v>>5)&63,v&31
    return ((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2))
BANDS=tuple(tuple(rgb565(x) for x in page) for page in BANDS565)
SOURCE={"nexium-archive.sha256"}|{"bridge/"+name for name in (
    "generated-input.json","dds-before.json","dds-after.json",
    "gpu-initial.png","gpu-later.png",MARKER,RECEIPT,"guest.log"
)}
PUBLIC=SOURCE-{"bridge/guest.log"}

def near(a,b,tol:int)->bool:
    return all(abs(a[k]-b[k])<=tol for k in range(3))

def _frame(path:Path)->dict:
    with Image.open(path) as source:
        image=source.convert("RGB")
    if image.size!=(1280,720):
        raise ValueError("Stage310 actual GPU image has wrong dimensions")
    pixel=image.load()
    bands={}
    last_y=0
    for index in range(8):
        l,r=BANDS[0][index],BANDS[1][index]
        mid=tuple((l[k]+r[k]+1)//2 for k in range(3))
        matches=[]
        for y in range(175,561):
            if (near(pixel[570,y],l,4) and
                near(pixel[710,y],r,4) and
                near(pixel[640,y],mid,23) and
                not near(pixel[640,y],l,8) and
                not near(pixel[640,y],r,8)):
                matches.append(y)
        # A single accidental match or a few linearly filtered boundary
        # pixels is NOT a valid stripe. Require >=12 contiguous rows.
        groups=[]
        run=[]
        for y in matches:
            if run and y!=run[-1]+1:
                groups.append(run)
                run=[]
            run.append(y)
        if run:groups.append(run)
        if not groups:raise ValueError("Stage310 stripe absent")
        longest=max(groups,key=len)
        if len(longest)<12:
            raise ValueError("Stage310 stripe too thin to be credible")
        center=longest[len(longest)//2]
        if center<last_y+16:
            raise ValueError("Stage310 eight stripes not in increasing order")
        last_y=center
        counts={}
        for label,x,expected,tol in (
            ("left",570,l,4),("right",710,r,4),("mixed",640,mid,23)
        ):
            count=sum(near(pixel[xx,yy],expected,tol)
                for xx in range(x-2,x+3)
                for yy in range(center-2,center+3))
            if count<22:
                raise ValueError("Stage310 GPU stripe RGB probe mismatch")
            counts[label]=count
        for x in (635,645):
            if near(pixel[x,center],l,8) or near(pixel[x,center],r,8):
                raise ValueError("Stage310 seam merely clamps one page")
        bands[str(index)]={"y":center,"match":counts}
    if len(bands)!=8:
        raise ValueError("Stage310 requires all eight independent stripes")
    return bands

def audit(bridge:Path)->dict:
    bridge=Path(bridge)
    if bridge.is_symlink() or not bridge.is_dir():
        raise ValueError("Stage310 unsafe guest evidence directory")
    if json.loads(_regular_file(bridge/"generated-input.json"))!=_origin():
        raise ValueError("Stage310 untrusted original DDS source")
    for when in ("before","after"):
        if json.loads(_regular_file(bridge/f"dds-{when}.json"))!=_attestation(when):
            raise ValueError("Stage310 changed synthetic DDS before/after")
    if _regular_file(bridge/MARKER)!=MARKER_BYTES:
        raise ValueError("Stage310 native marker absent or forged")
    a=bridge/"gpu-initial.png"
    b=bridge/"gpu-later.png"
    probes={p.name:_frame(p) for p in (a,b)}
    if not phase_changed(a,b):
        raise ValueError("Stage310 no distinct NeXium clear phases")
    return {
        "schema":"foj.stage310.eight_row_patterned_cross_page_gpu_gutter.v1",
        "eight_different_bc1_page_edge_pairs":True,
        "strict_gpu_midpoint_verified_each_row_band":True,
        "stripes_verified_per_frame":8,
        "two_actual_guest_frames_verified":2,
        "native_cpu_decoded_page_gutter_rows":256,
        "observed":probes,
        "original_ps3_assets_used":False,
        "original_game_uvs_verified":False,
        "hardware_cross_texture_bilinear_verified":False,
        "physical_switch_verified":False,
        "generated_only":True,
    }

def publish(source:Path,output:Path)->dict:
    source,output=Path(source),Path(output)
    if (output.exists() or output.is_symlink() or
        not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage310 publication must create a new directory")
    _check_tree(source,SOURCE)
    result=audit(source/"bridge")
    if json.loads(_regular_file(source/"bridge"/RECEIPT))!=result:
        raise ValueError("Stage310 report not identical to independent audit")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular_file(source/"nexium-archive.sha256")):
        raise ValueError("Stage310 guest archive digest not declared")
    output.mkdir(mode=0o700)
    try:
        (output/"bridge").mkdir(mode=0o700)
        for name in sorted(PUBLIC):
            cap=12*1024*1024 if name.endswith(".png") else 65536
            data=_regular_file(source/name,cap)
            with (output/name).open("xb") as fp:fp.write(data)
        _check_tree(output,PUBLIC)
        if audit(output/"bridge")!=result:
            raise ValueError("Stage310 public capture differs from private audit")
        for name in PUBLIC:
            cap=12*1024*1024 if name.endswith(".png") else 65536
            if _regular_file(output/name,cap)!=_regular_file(source/name,cap):
                raise ValueError("Stage310 failed exact exported byte comparison")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {"schema":"foj.stage310.generated_only_strict_eight_file_export.v1",
            "public_files":len(PUBLIC),"real_gpu_frames_verified":2,
            "private_game_data_uploaded":False,"guest_logs_uploaded":False}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("audit");a.add_argument("--evidence",type=Path,required=True)
    b=sub.add_parser("publish");b.add_argument("--source",type=Path,required=True)
    b.add_argument("--output",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=="audit":
            result=audit(args.evidence)
            _write_new(args.evidence,RECEIPT,result)
        else:result=publish(args.source,args.output)
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError):
        print("Stage310 generated-only GPU evidence refused.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
