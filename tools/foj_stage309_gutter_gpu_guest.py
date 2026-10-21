#!/usr/bin/env python3
"""Stage309 NeXium evidence: a real GPU-frame seam must show BOTH page
endpoint colors AND a nontrivial mixed color from the native gutter texture.
Host-generated PNG tests are refusals only; never assert emulator success.
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

MARKER="native-stage309-gutter-pass.txt"
RECEIPT="stage309-gutter-guest-receipt.json"
MARKER_BYTES=(b"FOJ_NATIVE_STAGE309_GUTTER_V1 pages=1,1+2,1 "
              b"contrast=blue-yellow/red-green verts=18 uv=interpolated\n")
ROWS=((280,(0,0,255),(255,255,0),(128,128,128)),
      (460,(255,0,0),(0,255,0),(128,128,0)))
SOURCES={"nexium-archive.sha256"}|{"bridge/"+name for name in (
    "generated-input.json","dds-before.json","dds-after.json",
    "gpu-initial.png","gpu-later.png",MARKER,RECEIPT,"guest.log"
)}
PUBLIC=SOURCES-{"bridge/guest.log"}

def _color_close(actual,expected,tolerance):
    return all(abs(actual[i]-expected[i])<=tolerance for i in range(3))

def _frame(p:Path):
    with Image.open(p) as image:
        rgb=image.convert("RGB")
    if rgb.size!=(1280,720):
        raise ValueError("Stage309 unexpected captured GPU frame dimensions")
    report={}
    for y,left,right,middle in ROWS:
        for label,x,expected,tol in (
            ("left",570,left,4),("right",710,right,4),
            ("mixed",640,middle,22),
        ):
            # The center gradient spans a narrow 37px foreground quad.
            # At x+/-3 its physically valid bilinear color can be >22
            # levels from the exact 50/50 midpoint. Check a tighter
            # 5x7 footprint at the center; keep 7x7 for flat endpoints.
            radius=2 if label=="mixed" else 3
            minimum=33 if label=="mixed" else 45
            count=sum(_color_close(rgb.getpixel((px,py)),expected,tol)
                      for py in range(y-3,y+4)
                      for px in range(x-radius,x+radius+1))
            if count<minimum:
                raise ValueError("Stage309 missing contrasting endpoints or seam mix")
            report[f"{y}_{label}"]=count
        center=rgb.getpixel((640,y))
        if (_color_close(center,left,8) or _color_close(center,right,8)):
            raise ValueError("Stage309 clamped single-page endpoint at seam")
        # Exact color discontinuity across the page transition without
        # gutter could appear as two solid halves: require intermediate
        # samples at the two screenshot columns beside the center.
        at_635=rgb.getpixel((635,y))
        at_645=rgb.getpixel((645,y))
        for pixel in (at_635,at_645):
            if _color_close(pixel,left,8) or _color_close(pixel,right,8):
                raise ValueError("Stage309 endpoint leak into seam gutter")
    return report

def phase_changed(a:Path,b:Path):
    with Image.open(a) as x,Image.open(b) as y:
        left=x.convert("RGB");right=y.convert("RGB")
    if left.size!=(1280,720) or right.size!=(1280,720):
        return False
    return sum(left.getpixel(pt)!=right.getpixel(pt)
               for pt in ((25,350),(1220,350),(640,650),(25,650)))>=3

def audit(folder:Path):
    folder=Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage309 unsafe frame location")
    if json.loads(_regular_file(folder/"generated-input.json"))!=_origin():
        raise ValueError("Stage309 unknown input source")
    for when in ("before","after"):
        if json.loads(_regular_file(folder/f"dds-{when}.json"))!=_attestation(when):
            raise ValueError("Stage309 generated DDS identity changed")
    if _regular_file(folder/MARKER)!=MARKER_BYTES:
        raise ValueError("Stage309 native seam descriptor missing or incorrect")
    imgs=[folder/"gpu-initial.png",folder/"gpu-later.png"]
    probes={p.name:_frame(p) for p in imgs}
    if not phase_changed(*imgs):
        raise ValueError("Stage309 two GPU background phases not observed")
    return {
        "schema":"foj.stage309.generated_gpu_cross_page_gutter.v1",
        "generated_only":True,
        "native_bc1_pages_and_18_vertex_seam_attested":True,
        "gpu_seam_endpoint_pair_colors_verified":True,
        "gpu_mixed_cross_page_color_verified":True,
        "real_neixum_frames_verified":2,
        "per_frame_probes":probes,
        "original_ps3_assets_used":False,
        "original_foj_uvs_tested":False,
        "hardware_filtering_on_independent_pages":False,
        "explicit_edge_gutter_strategy_tested":True,
        "physical_switch_tested":False,
    }

def publish(source:Path,output:Path):
    source,output=Path(source),Path(output)
    if (output.exists() or output.is_symlink() or
        not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage309 needs fresh public evidence directory")
    _check_tree(source,SOURCES)
    verification=audit(source/"bridge")
    recorded=json.loads(_regular_file(source/"bridge"/RECEIPT))
    if recorded!=verification:
        raise ValueError("Stage309 saved guest report not equal to fresh audit")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular_file(source/"nexium-archive.sha256")):
        raise ValueError("Stage309 invalid NeXium executable archive provenance")
    output.mkdir(mode=0o700)
    try:
        (output/"bridge").mkdir(mode=0o700)
        for relative in sorted(PUBLIC):
            limit=12*1024*1024 if relative.endswith(".png") else 65536
            body=_regular_file(source/relative,limit)
            with (output/relative).open("xb") as f:f.write(body)
        _check_tree(output,PUBLIC)
        if audit(output/"bridge")!=verification:
            raise ValueError("Stage309 public GPU evidence was changed")
        for relative in PUBLIC:
            limit=12*1024*1024 if relative.endswith(".png") else 65536
            if _regular_file(source/relative,limit)!=_regular_file(output/relative,limit):
                raise ValueError("Stage309 original guest evidence changed")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {"schema":"foj.stage309.generated_only_public_gpu_gutter.v1",
            "public_files":len(PUBLIC),"real_guest_frames_verified":2,
            "raw_log_uploaded":False,"original_ps3_assets_uploaded":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    a=sub.add_parser("audit");a.add_argument("--evidence",type=Path,required=True)
    b=sub.add_parser("publish");b.add_argument("--source",type=Path,required=True)
    b.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.action=="audit":
            result=audit(args.evidence);_write_new(args.evidence,RECEIPT,result)
        else:result=publish(args.source,args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        print("Stage309 generated-only GPU seam evidence refused.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
