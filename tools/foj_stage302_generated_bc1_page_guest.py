#!/usr/bin/env python3
"""Stage302 real guest evidence gate: decoded 1024 BC1 page must reach NeXium.

Host-created mock PNGs are ONLY for regression tests, never proof of GPU.
Actual GPU claim requires Stage274's guest drive and its two framebuffer
screenshots in the CI run alongside fresh native-authored receipts.
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
    _origin, _attestation, _write_new, audit as stage293_audit,
)

SCHEMA="foj.stage302.neixum_bc1_1024_generated_page.v1"
MARKER="native-stage302-paged-pass.txt"
RECEIPT="stage302-paged-bc1-guest-receipt.json"
EXPECTED_MARKER=b"FOJ_NATIVE_STAGE302_PAGE_V1 p=2,1 rgb=24,203,222 size=256\n"
PAGE_RGB=(24,203,222)
PUBLIC=(
    "generated-input.json", "dds-before.json", "dds-after.json",
    "gpu-initial.png", "gpu-later.png", "native-sort-pass.txt",
    "native-alpha-pass.txt", MARKER, RECEIPT,
)
HASH="nexium-archive.sha256"
SOURCE={HASH}|{"bridge/"+n for n in (*PUBLIC,"guest.log")}
EXPORTED={HASH}|{"bridge/"+n for n in PUBLIC}


def pixel_probe(path: Path) -> int:
    """Confirm selected page is *not* the original Stage293 cool fallback."""
    with Image.open(path) as image:
        image_rgb=image.convert("RGB")
    if image_rgb.size!=(1280,720):
        raise ValueError("Stage302 unexpected guest framebuffer dimensions")
    cx,cy=PROBES["rear_only"]
    counts=sum(all(abs(image_rgb.getpixel((x,y))[i]-PAGE_RGB[i])<=2
                   for i in range(3))
               for y in range(cy-5,cy+6)
               for x in range(cx-5,cx+6))
    if counts<116:
        raise ValueError("Stage302 selected BC1 page not visible in GPU framebuffer")
    return counts


def audit(evidence: Path) -> dict:
    root=Path(evidence)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Stage302 guest evidence root unsafe")
    checked=stage293_audit(root)
    if checked["guest_frames_verified"]!=2 or not checked["generated_only"]:
        raise ValueError("Stage302 Stage293 guest evidence invariant changed")
    if _regular_file(root/MARKER)!=EXPECTED_MARKER:
        raise ValueError("Stage302 native guest did not attest selected page")
    matches={
        name:pixel_probe(root/name)
        for name in ("gpu-initial.png","gpu-later.png")
    }
    if len(matches)!=2:
        raise ValueError("Stage302 missing two guest framebuffer views")
    return {
        "schema":SCHEMA,
        "real_neixum_guest_frames_verified":2,
        "native_stage302_page_receipt_verified":True,
        "native_sort_and_alpha_receipts_verified":True,
        "stage292_converted_dds_input_bound":True,
        "generated_1024_bc1_source_created_in_native_c":True,
        "actual_stage301_page_decoder_called_in_native_c":True,
        "gpu_rear_page_rgb":list(PAGE_RGB),
        "gpu_page_probe_tolerance":2,
        "gpu_page_probe_matches":matches,
        "selected_page":{"x":2,"y":1,"width":256,"height":256},
        "stage293_underlying_gpu_probe_verified":True,
        "generated_only":True,
        "original_ps3_assets_used":False,
        "original_foj_material_mapping_verified":False,
        "original_1024_game_atlas_gpu_verified":False,
        "physical_switch_verified":False,
    }


def publish(source: Path, output: Path) -> dict:
    source,output=Path(source),Path(output)
    if (output.exists() or output.is_symlink() or
            not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage302 requires a new evidence publication directory")
    _check_tree(source,SOURCE)
    checked=audit(source/"bridge")
    saved=json.loads(_regular_file(source/"bridge"/RECEIPT))
    if saved!=checked:
        raise ValueError("Stage302 saved report differs from fresh guest re-audit")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular_file(source/HASH)):
        raise ValueError("Stage302 expected immutable NeXium archive provenance")
    output.mkdir(mode=0o700)
    try:
        (output/"bridge").mkdir(mode=0o700)
        for relative in sorted(EXPORTED):
            item=source/relative
            max_bytes=12*1024*1024 if item.name.startswith("gpu-") else 65536
            payload=_regular_file(item,max_bytes)
            with (output/relative).open("xb") as handle:
                handle.write(payload)
        _check_tree(output,EXPORTED)
        if audit(output/"bridge")!=checked:
            raise ValueError("Stage302 public evidence changed after copy")
        for relative in EXPORTED:
            item=source/relative
            limit=12*1024*1024 if item.name.startswith("gpu-") else 65536
            if _regular_file(item,limit)!=_regular_file(output/relative,limit):
                raise ValueError("Stage302 source evidence changed after copy")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema":"foj.stage302.public_page_gpu_evidence.v1",
        "public_files":len(EXPORTED),"generated_only":True,
        "raw_guest_log_uploaded":False,"private_manifest_uploaded":False,
        "real_neixum_guest_frames_verified":2,
        "original_game_assets_uploaded":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    q=p.add_subparsers(dest="action",required=True)
    a=q.add_parser("audit")
    a.add_argument("--evidence",required=True,type=Path)
    b=q.add_parser("publish")
    b.add_argument("--source",required=True,type=Path)
    b.add_argument("--output",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        if args.action=="audit":
            result=audit(args.evidence)
            _write_new(args.evidence,RECEIPT,result)
        else:
            result=publish(args.source,args.output)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        print("Stage302 generated-only NeXium page evidence refused.",file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
