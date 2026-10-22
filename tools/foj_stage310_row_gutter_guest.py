#!/usr/bin/env python3
"""Stage310: prove eight synthetic BC1 cross-page gutter blends in two
ACTUAL NeXium guest screenshots. Host mock tests are rejection logic only.
No owner-original PS3 resources can be included in public evidence.
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

MARKER="native-stage310-row-gutter-pass.txt"
RECEIPT="stage310-row-gutter-receipt.json"
MARKER_BYTES=(b"FOJ_NATIVE_STAGE310_ROW_GUTTER_V1 pairs=8 rows=256 "
              b"strict_mix=256 pages=1,1+2,1 verts=18\n")
LEFT565=(0x001f,0xf800,0x07e0,0xffe0,0xf81f,0x07ff,0xffff,0x0000)
RIGHT565=(0xffe0,0x07e0,0x001f,0xf800,0x07ff,0xf81f,0x0000,0xffff)
Y_CENTERS=(195,238,282,325,368,412,455,498)
SOURCE={"nexium-archive.sha256"}|{"bridge/"+p for p in
    ("generated-input.json","dds-before.json","dds-after.json",
     "gpu-initial.png","gpu-later.png",MARKER,RECEIPT,"guest.log")}
PUBLIC=SOURCE-{"bridge/guest.log"}

def expand565(code:int)->tuple[int,int,int]:
    r=(code>>11)&31
    g=(code>>5)&63
    b=code&31
    return ((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2))

def close(color,expected,tol):
    return all(abs(color[c]-expected[c])<=tol for c in range(3))

def _frame(path:Path)->dict:
    with Image.open(path) as original:
        image=original.convert("RGB")
    if image.size!=(1280,720):
        raise ValueError("Stage310 framebuffer mismatch")
    report={}
    for i,y in enumerate(Y_CENTERS):
        lo=expand565(LEFT565[i])
        ri=expand565(RIGHT565[i])
        middle=tuple((a+b+1)//2 for a,b in zip(lo,ri))
        for label,x,color,tol,radius,needed in (
            ("left",570,lo,4,3,45),
            ("right",710,ri,4,3,45),
            ("midpoint",640,middle,22,2,33),
        ):
            found=sum(close(image.getpixel((px,py)),color,tol)
                      for py in range(y-3,y+4)
                      for px in range(x-radius,x+radius+1))
            if found<needed:
                raise ValueError(f"Stage310 band={i} {label} color absent")
            report[f"band{i}_{label}"]=found
        seam=image.getpixel((640,y))
        if close(seam,lo,8) or close(seam,ri,8):
            raise ValueError("Stage310 clamped page endpoint instead of bilinear")
        for near_x in (635,645):
            if close(image.getpixel((near_x,y)),lo,8) or \
               close(image.getpixel((near_x,y)),ri,8):
                raise ValueError("Stage310 independent page leaked into gutter")
    return report

def _phases(a:Path,b:Path)->bool:
    with Image.open(a) as before, Image.open(b) as after:
        x,y=before.convert("RGB"),after.convert("RGB")
    if x.size!=(1280,720) or y.size!=(1280,720):
        return False
    return sum(x.getpixel(pt)!=y.getpixel(pt) for pt in
               ((25,350),(1220,350),(640,650),(25,650)))>=3

def audit(folder:Path)->dict:
    folder=Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage310 unsafe evidence folder")
    if json.loads(_regular_file(folder/"generated-input.json"))!=_origin():
        raise ValueError("Stage310 unknown source")
    for phase in ("before","after"):
        if json.loads(_regular_file(folder/f"dds-{phase}.json"))!=_attestation(phase):
            raise ValueError("Stage310 source DDS identity changed")
    if _regular_file(folder/MARKER)!=MARKER_BYTES:
        raise ValueError("Stage310 guest marker wrong")
    first=folder/"gpu-initial.png"
    second=folder/"gpu-later.png"
    probes={first.name:_frame(first),second.name:_frame(second)}
    if not _phases(first,second):
        raise ValueError("Stage310 cannot confirm separate GPU clear phases")
    return {
        "schema":"foj.stage310.eight_row_bands_two_page_bilinear_gutter.gpu.v1",
        "real_neixum_guest_frames_verified":2,
        "color_pairs_per_frame":8,
        "per_frame_pixel_probes":probes,
        "native_256_row_input_mix_contract_attested":True,
        "all_eight_gpu_edge_color_pairs_and_midpoints_verified":True,
        "original_ps3_assets_used":False,
        "hardware_switch_verified":False,
        "general_original_game_material_mapping_verified":False,
        "independent_sampler_cross_page_bilinear_verified":False,
        "generated_only":True,
    }

def publish(source:Path,target:Path)->dict:
    source,target=Path(source),Path(target)
    if (target.exists() or target.is_symlink() or
        not target.parent.is_dir() or target.parent.is_symlink()):
        raise ValueError("Stage310 only new public evidence directory")
    _check_tree(source,SOURCE)
    expected=audit(source/"bridge")
    if json.loads(_regular_file(source/"bridge"/RECEIPT))!=expected:
        raise ValueError("Stage310 saved report inconsistent with real screenshots")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular_file(source/"nexium-archive.sha256")):
        raise ValueError("Stage310 invalid release artifact pin")
    target.mkdir(mode=0o700)
    try:
        (target/"bridge").mkdir(mode=0o700)
        for item in sorted(PUBLIC):
            limit=12*1024*1024 if item.endswith(".png") else 65536
            body=_regular_file(source/item,limit)
            with (target/item).open("xb") as f:
                f.write(body)
        _check_tree(target,PUBLIC)
        if audit(target/"bridge")!=expected:
            raise ValueError("Stage310 evidence not reproducible after export")
        for item in PUBLIC:
            limit=12*1024*1024 if item.endswith(".png") else 65536
            if (_regular_file(source/item,limit) !=
                _regular_file(target/item,limit)):
                raise ValueError("Stage310 evidence changed during export")
    except BaseException:
        shutil.rmtree(target)
        raise
    return {"schema":"foj.stage310.strict_generated_only_evidence_export.v1",
            "public_files":len(PUBLIC),"raw_guest_log_uploaded":False,
            "owner_original_assets_uploaded":False}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    subs=ap.add_subparsers(dest="cmd",required=True)
    a=subs.add_parser("audit");a.add_argument("--evidence",type=Path,required=True)
    b=subs.add_parser("publish");b.add_argument("--source",type=Path,required=True)
    b.add_argument("--output",type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if args.cmd=="audit":
            result=audit(args.evidence)
            _write_new(args.evidence,RECEIPT,result)
        else:
            result=publish(args.source,args.output)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError):
        print("Stage310 generated-only row-gutter GPU evidence refused.",
              file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
