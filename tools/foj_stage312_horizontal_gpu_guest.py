#!/usr/bin/env python3
"""Strict Stage312 real NeXium horizontal BC1 page-edge GPU evidence.

Synthetic screenshots in unittest do NOT establish an emulator run.
Publish only the independently verified real two-phase GPU evidence.
"""
from __future__ import annotations
import argparse,json,re,shutil,sys
from pathlib import Path
from PIL import Image
from tools.foj_stage289_public_guest_evidence import _check_tree,_regular_file
from tools.foj_stage293_converted_dds_guest import _origin,_attestation,_write_new
from tools.foj_stage309_gutter_gpu_guest import phase_changed

MARKER="native-stage312-horizontal-gutter-pass.txt"
RECEIPT="stage312-horizontal-gutter-guest-receipt.json"
MARKER_BYTES=(b"FOJ_NATIVE_STAGE312_HORIZONTAL_GUTTER_V1 pairs=8 "
              b"columns=256 strict_mix=256 pages=1,1+1,2 verts=18\n")
PAIRS565=(
    (0x001f,0xf800,0x07e0,0xffe0,0xf81f,0x07ff,0xffff,0x0000),
    (0xffe0,0x07e0,0x001f,0xf800,0x07ff,0xf81f,0x0000,0xffff)
)
X_CENTERS=(315,407,500,592,685,777,870,962)
SOURCE={"nexium-archive.sha256"}|{"bridge/"+n for n in (
    "generated-input.json","dds-before.json","dds-after.json",
    "gpu-initial.png","gpu-later.png",MARKER,RECEIPT,"guest.log")}
PUBLIC=SOURCE-{"bridge/guest.log"}

def rgb565(v:int):
    r,g,b=(v>>11)&31,(v>>5)&63,v&31
    return ((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2))

def close_rgb(a,b,t:int):
    return all(abs(a[k]-b[k])<=t for k in range(3))

def _frame(path:Path)->dict:
    with Image.open(path) as opened:
        im=opened.convert("RGB")
    if im.size!=(1280,720):
        raise ValueError("Stage312 wrong real NeXium screenshot dimensions")
    pixel=im.load()
    found={}
    seam_centers=[]
    for stripe,x in enumerate(X_CENTERS):
        top=rgb565(PAIRS565[0][stripe])
        bottom=rgb565(PAIRS565[1][stripe])
        mixed=tuple((top[k]+bottom[k]+1)//2 for k in range(3))
        # Endpoint stripes are independently verified away from the
        # seam: do not infer their colors from a mixed RGB midpoint.
        for label,y,rgb in (("top",280,top),("bottom",460,bottom)):
            count=sum(close_rgb(pixel[px,py],rgb,4)
                      for px in range(x-3,x+4)
                      for py in range(y-3,y+4))
            if count<45:
                raise ValueError(
                    f"Stage312 stripe={stripe} {label} GPU colors absent")
            found[f"band{stripe}_{label}"]=count

        # NeXium's presentation viewport shifts the projected seam.
        # A previous real frame placed the actual 50/50 reconstruction
        # near Y=346, not nominal Y=360. Locate the midpoint by COLOR
        # in a strictly bounded 326..370 search rather than accepting
        # any isolated intermediate pixel.
        candidates=[]
        for y in range(326,371):
            rgb=pixel[x,y]
            if close_rgb(rgb,mixed,16):
                error=max(abs(rgb[k]-mixed[k]) for k in range(3))
                candidates.append((error,y))
        if not candidates:
            raise ValueError(
                f"Stage312 stripe={stripe} missing real GPU midpoint")
        _,center=min(candidates)
        count=sum(close_rgb(pixel[px,py],mixed,22)
                  for px in range(x-3,x+4)
                  for py in range(center-1,center+2))
        if count<18:
            raise ValueError(
                f"Stage312 stripe={stripe} midpoint not a coherent 7x3 region")
        # Two physically separated interior points must have different
        # intermediate colors. This rejects an abrupt independent-page
        # step, a solid synthetic midpoint bar, and leaked endpoints.
        before=pixel[x,center-6]
        after=pixel[x,center+6]
        for sample in (before,after,pixel[x,center]):
            if close_rgb(sample,top,8) or close_rgb(sample,bottom,8):
                raise ValueError(
                    f"Stage312 stripe={stripe} seam leaks a page endpoint")
        if max(abs(before[k]-after[k]) for k in range(3))<16:
            raise ValueError(
                f"Stage312 stripe={stripe} no actual GPU color gradient")
        seam_centers.append(center)
        found[f"band{stripe}_mixed"]=count
        found[f"band{stripe}_seam_y"]=center

    # Every stripe uses the same native horizontal quad, so the screen
    # midpoint cannot jump independently between neighboring stripes.
    if max(seam_centers)-min(seam_centers)>2:
        raise ValueError("Stage312 incoherent horizontal GPU seam location")
    return found

def audit(folder:Path):
    folder=Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage312 invalid evidence folder")
    if json.loads(_regular_file(folder/"generated-input.json"))!=_origin():
        raise ValueError("Stage312 source not synthetic")
    for phase in ("before","after"):
        if json.loads(_regular_file(folder/f"dds-{phase}.json"))!=_attestation(phase):
            raise ValueError("Stage312 synthetic source changed")
    if _regular_file(folder/MARKER)!=MARKER_BYTES:
        raise ValueError("Stage312 guest did not write horizontal seam receipt")
    first=folder/"gpu-initial.png"
    second=folder/"gpu-later.png"
    probes={path.name:_frame(path) for path in (first,second)}
    if not phase_changed(first,second):
        raise ValueError("Stage312 only one framebuffer clear phase")
    return {
        "schema":"foj.stage312.actual_gpu_horizontal_bc1_gutter.v1",
        "generated_only":True,
        "native_256_column_horizontal_gutter_attested":True,
        "real_neixum_guest_frames_verified":2,
        "column_color_pairs_per_frame":8,
        "per_frame_pixel_probes":probes,
        "actual_horizontal_gpu_seam_midpoints_verified":True,
        "independent_page_bilinear_reconstruction_verified":False,
        "original_ps3_assets_used":False,
        "physical_switch_verified":False,
    }

def publish(source:Path,output:Path):
    source,output=Path(source),Path(output)
    if (output.exists() or output.is_symlink() or
        not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage312 refuses preexisting output")
    _check_tree(source,SOURCE)
    verified=audit(source/"bridge")
    if json.loads(_regular_file(source/"bridge"/RECEIPT))!=verified:
        raise ValueError("Stage312 report differs from independent fresh audit")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular_file(source/"nexium-archive.sha256")):
        raise ValueError("Stage312 NeXium binary digest missing")
    output.mkdir(mode=0o700)
    try:
        (output/"bridge").mkdir(mode=0o700)
        for item in sorted(PUBLIC):
            cap=12*1024*1024 if item.endswith(".png") else 65536
            with (output/item).open("xb") as stream:
                stream.write(_regular_file(source/item,cap))
        _check_tree(output,PUBLIC)
        if audit(output/"bridge")!=verified:
            raise ValueError("Stage312 public evidence altered")
        for item in PUBLIC:
            cap=12*1024*1024 if item.endswith(".png") else 65536
            if _regular_file(source/item,cap)!=_regular_file(output/item,cap):
                raise ValueError("Stage312 file copy provenance mismatch")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {"schema":"foj.stage312.strict_generated_only_evidence.v1",
            "public_files":len(PUBLIC),"real_frames":2,
            "private_game_bytes_uploaded":False,"raw_guest_log_uploaded":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("audit");a.add_argument("--evidence",type=Path,required=True)
    b=sub.add_parser("publish");b.add_argument("--source",type=Path,required=True)
    b.add_argument("--output",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.action=="audit":
            out=audit(args.evidence)
            _write_new(args.evidence,RECEIPT,out)
        else:out=publish(args.source,args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        print("Stage312 generated-only horizontal GPU evidence refused.",file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
