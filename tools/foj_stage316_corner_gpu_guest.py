#!/usr/bin/env python3
"""Stage316 strict two-frame NeXium GPU proof of four-source BC1 corner mixing.

The guest must render a genuine GPU bilinear 2D gradient in a synthetic atlas
junction. Host-fabricated PNGs are *negative-test fixtures only*.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from PIL import Image
from tools.foj_stage289_public_guest_evidence import _check_tree, _regular_file
from tools.foj_stage293_converted_dds_guest import _origin, _attestation, _write_new
from tools.foj_stage309_gutter_gpu_guest import phase_changed

MARKER = "native-stage316-four-corner-pass.txt"
RECEIPT = "stage316-four-corner-gpu-receipt.json"
MARKER_BYTES = (
    b"FOJ_NATIVE_STAGE316_FOUR_CORNER_V1 "
    b"pages=1,1+2,1+1,2+2,2 colors=4 strict_center=1 verts=18\n"
)
SOURCE = {"nexium-archive.sha256"} | {"bridge/"+f for f in (
    "generated-input.json", "dds-before.json", "dds-after.json",
    "gpu-initial.png", "gpu-later.png", MARKER, RECEIPT, "guest.log",
)}
PUBLIC = SOURCE-{"bridge/guest.log"}
CORNERS = (
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255),
)

def close_rgb(a, b, tolerance):
    return all(abs(int(a[k])-int(b[k])) <= tolerance for k in range(3))

def _frame(path: Path) -> dict:
    with Image.open(path) as image:
        im = image.convert("RGB")
    if im.size != (1280, 720):
        raise ValueError("Stage316 invalid native screenshot dimensions")
    pixels = im.load()
    candidates = []
    # Native viewport is inset from the nominal center. Search only an
    # empirically bounded central footprint; never accept edge/backdrop RGB.
    for y in range(310, 381):
        for x in range(590, 691, 2):
            if close_rgb(pixels[x,y],(128,128,128),18):
                count = sum(close_rgb(pixels[xx,yy],(128,128,128),24)
                            for xx in range(x-2,x+3)
                            for yy in range(y-2,y+3))
                if count >= 22:
                    candidates.append((abs(x-640)+abs(y-346),x,y,count))
    if not candidates:
        raise ValueError("Stage316 genuine four-source midpoint absent")
    _,cx,cy,mid_count = min(candidates)
    # A painted 2D midpoint *bar* can mimic the central 5x5 color.
    # Independently demand a nonconstant local gradient around it too.
    if pixels[cx+7,cy][1]-pixels[cx-7,cy][1] < 4 or \
       pixels[cx,cy+7][2]-pixels[cx,cy-7][2] < 6:
        raise ValueError("Stage316 a flat painted center bar is not GPU filtering")
    sample = {}
    for i,dy in enumerate((-45, 0, 45)):
        for j,dx in enumerate((-65, 0, 65)):
            sample[f"r{i}c{j}"] = list(pixels[cx+dx,cy+dy])
    # The invented colors satisfy G=255*tx and B=255*ty (R depends on
    # both), so two-axis behavior cannot be forged by an edge-only blend.
    for i in range(3):
        if sample[f"r{i}c2"][1]-sample[f"r{i}c0"][1] < 35:
            raise ValueError("Stage316 missing genuine horizontal green gradient")
    for j in range(3):
        if sample[f"r2c{j}"][2]-sample[f"r0c{j}"][2] < 35:
            raise ValueError("Stage316 missing genuine vertical blue gradient")
    nw = sample["r0c0"][0]
    ne = sample["r0c2"][0]
    sw = sample["r2c0"][0]
    se = sample["r2c2"][0]
    if nw-ne < 8 or se-sw < 8:
        raise ValueError("Stage316 red checkerboard four-way term absent")
    # Four independently distinguishable quadrant endpoints must be
    # visible inside the front corner patch, not only its side backplates.
    endpoints = {}
    for name, color, signx, signy in (
        ("nw", CORNERS[0], -1, -1), ("ne", CORNERS[1], 1, -1),
        ("sw", CORNERS[2], -1, 1), ("se", CORNERS[3], 1, 1),
    ):
        best = 0
        for dy in range(113, 159, 5):
            for dx in range(218, 270, 5):
                x, y = cx+signx*dx, cy+signy*dy
                count = sum(close_rgb(pixels[xx,yy],color,60)
                            for xx in range(x-2,x+3)
                            for yy in range(y-2,y+3))
                best = max(best,count)
        if best < 20:
            raise ValueError(f"Stage316 native quadrant {name} color absent")
        endpoints[name] = best
    return {
        "center_x":cx,"center_y":cy,
        "midpoint_matching_pixels":mid_count,
        "independent_corner_color_regions":endpoints,
        "two_dimensional_samples":sample,
    }

def audit(folder: Path) -> dict:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage316 invalid evidence folder")
    if json.loads(_regular_file(folder/"generated-input.json")) != _origin():
        raise ValueError("Stage316 non-synthetic source")
    for phase in ("before","after"):
        if json.loads(_regular_file(folder/f"dds-{phase}.json")) != _attestation(phase):
            raise ValueError("Stage316 synthetic source changed")
    if _regular_file(folder/MARKER) != MARKER_BYTES:
        raise ValueError("Stage316 incorrect native guest corner marker")
    a,b=(folder/"gpu-initial.png",folder/"gpu-later.png")
    frames={p.name:_frame(p) for p in (a,b)}
    if not phase_changed(a,b):
        raise ValueError("Stage316 duplicate framebuffer phases")
    if abs(frames[a.name]["center_x"]-frames[b.name]["center_x"])>2 or \
       abs(frames[a.name]["center_y"]-frames[b.name]["center_y"])>2:
        raise ValueError("Stage316 drifting screenshot center")
    return {
        "schema":"foj.stage316.real_four_page_gpu_corner.v1",
        "generated_only":True,
        "native_four_page_material_attested":True,
        "real_neixum_frames_verified":2,
        "corners_verified_per_frame":4,
        "genuine_two_axis_bilinear_gradient_verified":True,
        "per_frame_probes":frames,
        "original_ps3_assets_used":False,
        "physical_switch_verified":False,
        "automatic_cross_texture_bilinear_verified":False,
    }

def publish(source: Path, output: Path) -> dict:
    source,output=Path(source),Path(output)
    if output.exists() or output.is_symlink() or \
       not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("Stage316 refuses existing output")
    _check_tree(source,SOURCE)
    checked=audit(source/"bridge")
    if json.loads(_regular_file(source/"bridge"/RECEIPT))!=checked:
        raise ValueError("Stage316 saved report differs from fresh audit")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular_file(source/"nexium-archive.sha256")):
        raise ValueError("Stage316 NeXium archive not pinned")
    output.mkdir(mode=0o700)
    try:
        (output/"bridge").mkdir(mode=0o700)
        for name in sorted(PUBLIC):
            limit=12*1024*1024 if name.endswith(".png") else 65536
            contents=_regular_file(source/name,limit)
            with (output/name).open("xb") as handle:
                handle.write(contents)
        _check_tree(output,PUBLIC)
        if audit(output/"bridge")!=checked:
            raise ValueError("Stage316 public proof mismatch")
        for name in PUBLIC:
            limit=12*1024*1024 if name.endswith(".png") else 65536
            if _regular_file(source/name,limit)!=_regular_file(output/name,limit):
                raise ValueError("Stage316 public evidence bytes altered")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema":"foj.stage316.strict_generated_only_evidence.v1",
        "public_files":len(PUBLIC),"real_frames":2,
        "private_game_bytes_uploaded":False,"guest_log_uploaded":False,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_subparsers(dest="mode",required=True)
    a=modes.add_parser("audit");a.add_argument("--evidence",type=Path,required=True)
    p=modes.add_parser("publish")
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.mode=="audit":
            result=audit(args.evidence)
            _write_new(args.evidence,RECEIPT,result)
        else: result=publish(args.source,args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        print("Stage316 independent GPU corner evidence refused.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
