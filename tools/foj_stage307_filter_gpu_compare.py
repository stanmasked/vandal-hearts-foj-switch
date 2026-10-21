#!/usr/bin/env python3
"""Stage307: compare *real* generated-only NeXium nearest/linear GPU frames.

Mock images test refusal logic, NOT emulator evidence. This cannot establish
bilinear reconstruction over the boundary of two independent page textures.
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
from tools.foj_stage306_patterned_uv_guest import audit as stage306_audit
from tools.foj_stage306_patterned_uv_guest import SOURCE as OLD_SOURCE
from tools.foj_stage306_patterned_uv_guest import PUBLIC as OLD_PUBLIC

MODES=("nearest","linear")
MARKER="native-stage307-filter-pass.txt"
EXPECTED={
    mode:("FOJ_NATIVE_STAGE307_FILTER_V1 mode="+mode+
          " mag="+mode+" min="+mode+" clamp=edge\n").encode()
    for mode in MODES
}
SOURCE=OLD_SOURCE|{"bridge/"+MARKER}
PUBLIC=OLD_PUBLIC|{"bridge/"+MARKER}
# Each edge is between two of four colored BC1 bands in one page.
EDGES={"left":(352,448,544),"right":(736,832,928)}
COLORS={
 "left":((255,0,0),(255,130,0),(0,0,255),(0,255,255)),
 "right":((0,255,255),(255,0,255),(0,255,0),(255,255,0)),
}

def audit(root:Path,mode:str)->dict:
    if mode not in MODES:raise ValueError("Stage307 unknown filter mode")
    root=Path(root)
    prior=stage306_audit(root)
    if _regular_file(root/MARKER)!=EXPECTED[mode]:
        raise ValueError("Stage307 mismatched guest-authored filter mode")
    return {"schema":"foj.stage307.generated_filter_guest.v1",
            "mode":mode,
            "stage306_eight_bands_verified":prior["interpolated_uv_bands_verified"]==8,
            "real_guest_frames_verified":prior["real_neixum_guest_frames_verified"],
            "native_exact_filter_receipt":True,
            "generated_only":True,
            "original_ps3_assets_used":False,
            "physical_switch_verified":False}

def _pixel(frame:Image.Image,x:int,y:int)->tuple:
    return frame.getpixel((x,y))

def compare(left:Path,right:Path)->dict:
    left,right=Path(left),Path(right)
    for folder,mode in ((left,"nearest"),(right,"linear")):
        _check_tree(folder,PUBLIC)
        if not audit(folder/"bridge",mode)["stage306_eight_bands_verified"]:
            raise ValueError("Stage307 prior eight-band proof lost")
    probes={}
    for filename in ("gpu-initial.png","gpu-later.png"):
        with Image.open(left/"bridge"/filename) as aa:
            n=aa.convert("RGB")
        with Image.open(right/"bridge"/filename) as bb:
            l=bb.convert("RGB")
        if n.size!=(1280,720) or l.size!=(1280,720):
            raise ValueError("Stage307 changed guest framebuffer size")
        differences=0
        samples=0
        for side,locations in EDGES.items():
            for band,boundary in enumerate(locations):
                before,after=COLORS[side][band:band+2]
                # NeXium's captured client framebuffer includes a small
                # presentation/viewport inset: 1280 pixels in the PNG do
                # not imply clip x=-0.6 begins exactly at x=256. Locate
                # each nearest *actual step* inside a tightly bounded
                # +/-16px search window, preserving exact color and band
                # order. Then compare LINEAR at that SAME measured edge.
                candidates=[]
                for x in range(boundary-16,boundary+17):
                    if x<=0 or x>=1280:
                        continue
                    prev=_pixel(n,x-1,400)
                    following=_pixel(n,x,400)
                    if (all(abs(prev[k]-before[k])<=4 for k in range(3))
                            and all(abs(following[k]-after[k])<=4
                                    for k in range(3))):
                        candidates.append(x)
                if len(candidates)!=1:
                    raise ValueError(
                        f"Stage307 {side} band={band} expected nearest step "
                        f"within +/-16px of x={boundary}; found={candidates}")
                edge=candidates[0]
                for x,nearest_color in ((edge-1,before),(edge,after)):
                    samples+=1
                    exact=_pixel(n,x,400)
                    smoothed=_pixel(l,x,400)
                    if any(abs(exact[k]-nearest_color[k])>4 for k in range(3)):
                        raise ValueError(
                            f"Stage307 nearest edge {side} band={band} x={x} "
                            f"expected={nearest_color} observed={exact}")
                    if any(smoothed[k]<min(before[k],after[k])-8 or
                           smoothed[k]>max(before[k],after[k])+8 for k in range(3)):
                        raise ValueError(
                            f"Stage307 linear edge {side} band={band} x={x} "
                            f"endpoints={before},{after} observed={smoothed}")
                    if max(abs(exact[k]-smoothed[k]) for k in range(3))>=14:
                        differences+=1
        # Six transition pairs, two pixels each; permit GPU quantization
        # and sample position variations, but reject equal nearest outputs.
        if differences<8:
            raise ValueError(
                f"Stage307 nearest/linear transition proof: "
                f"{differences}/{samples} pixels differed by >=14 RGB levels")
        probes[filename]={"transition_samples":samples,
                          "intermediate_differences":differences}
    return {"schema":"foj.stage307.two_real_gpu_filter_modes_compared.v1",
            "two_real_guest_modes":list(MODES),
            "guest_frames_audited":4,
            "per_phase_transition":probes,
            "generated_only":True,
            "within_page_linear_transition_observed":True,
            "inter_page_bilinear_reconstruction_verified":False,
            "original_foj_assets_verified":False,
            "physical_switch_verified":False}

def publish(source:Path,output:Path,mode:str)->dict:
    source,output=Path(source),Path(output)
    if (output.exists() or output.is_symlink() or
        not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage307 requires fresh publication directory")
    _check_tree(source,SOURCE)
    audit(source/"bridge",mode)
    checksum=_regular_file(source/"nexium-archive.sha256")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",checksum):
        raise ValueError("Stage307 NeXium archive identity missing")
    output.mkdir(mode=0o700)
    try:
        (output/"bridge").mkdir(mode=0o700)
        for path in sorted(PUBLIC):
            limit=12*1024*1024 if path.endswith(".png") else 65536
            data=_regular_file(source/path,limit)
            with (output/path).open("xb") as stream:stream.write(data)
        _check_tree(output,PUBLIC)
        if audit(output/"bridge",mode)!=audit(source/"bridge",mode):
            raise ValueError("Stage307 audit changed after copying")
        for path in PUBLIC:
            limit=12*1024*1024 if path.endswith(".png") else 65536
            if _regular_file(output/path,limit)!=_regular_file(source/path,limit):
                raise ValueError("Stage307 provenance copied incompletely")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {"schema":"foj.stage307.strict_generated_filter_evidence_public.v1",
            "mode":mode,"public_files":len(PUBLIC),"raw_guest_log_uploaded":False,
            "original_ps3_assets_uploaded":False}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("audit");a.add_argument("--mode",choices=MODES,required=True)
    a.add_argument("--root",type=Path,required=True)
    b=sub.add_parser("publish");b.add_argument("--mode",choices=MODES,required=True)
    b.add_argument("--source",type=Path,required=True)
    b.add_argument("--output",type=Path,required=True)
    c=sub.add_parser("compare");c.add_argument("--nearest",type=Path,required=True)
    c.add_argument("--linear",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=="audit": result=audit(args.root,args.mode)
        elif args.command=="publish":result=publish(args.source,args.output,args.mode)
        else:result=compare(args.nearest,args.linear)
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        if args.command=="compare" and isinstance(exc,ValueError):
            # All authored ValueError strings contain generated-only pixel
            # coordinates/quantized colors; not owner-private file paths.
            print(str(exc),file=sys.stderr)
        else:
            print("Stage307 filter evidence refused.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
