#!/usr/bin/env python3
"""Stage278: invented four-level 0/64/128/255 alpha staircase inside ONE generated RGBA8 DDS.

Reuses the proven Stage275 research NRO unchanged. Never accepts a PS3
texture, pre-existing SD root or arbitrary user image. Only public
generated three-triangle actor, two constant atlases, public shaders and
one deterministic per-texel-alpha near atlas are installed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from tools.foj_stage273_dynamic_gpu_sd import install_dynamic
from tools.foj_stage267_generated_multiblend_sd import SUBDIR
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import (
    COOL, WARM, VIOLET, Layer, order_layers, composite_rgb,
)

CASES=("staircase-ascending","staircase-descending")
SCHEMA="foj.stage278.four_band_alpha_generated_dds.v1"
WIDTH=64
BAND_SPLITS=(40,44,49)
ATLAS_NAME="material0.dds"
PROBES={"band_0":(605,400),"band_1":(630,400),
        "band_2":(651,400),"band_3":(675,400),
        "rear_only":(760,400)}
ALPHA_BANDS={
    "staircase-ascending":(0,64,128,255),
    "staircase-descending":(255,128,64,0),
}
BAND_NAMES=("band_0","band_1","band_2","band_3")


def near_atlas(case:str)->bytes:
    if case not in CASES:
        raise ValueError("Unknown spatial-alpha case")
    data=bytearray(generated_dds((*VIOLET,128)))
    if len(data)!=128+WIDTH*WIDTH*4:
        raise ValueError("Generated DDS layout changed")
    for y in range(WIDTH):
        for x in range(WIDTH):
            band=(0 if x<BAND_SPLITS[0] else
                  1 if x<BAND_SPLITS[1] else
                  2 if x<BAND_SPLITS[2] else 3)
            data[128+4*(y*WIDTH+x)+3]=ALPHA_BANDS[case][band]
    return bytes(data)


def target_rgb(alpha:int)->tuple[int,int,int]:
    if type(alpha) is not int or alpha not in (0,64,128,255):
        raise ValueError("Unsupported generated alpha")
    layers=(
        Layer("rear",.20,(*COOL,255),"opaque_rear"),
        Layer("middle",.55,(*WARM,128),"translucent_front"),
        Layer("near",.85,(*VIOLET,alpha),"translucent_front"),
    )
    return composite_rgb(order_layers(layers))


def expected_at(case:str,probe:str)->tuple[int,int,int]:
    if case not in CASES or probe not in PROBES:
        raise ValueError("Unknown spatial-alpha probe")
    if probe=="rear_only":
        return COOL
    return target_rgb(ALPHA_BANDS[case][BAND_NAMES.index(probe)])


def install_masked(root:Path,shaders:Path,case:str)->dict:
    if case not in CASES:
        raise ValueError("Unknown Stage278 case")
    payload=near_atlas(case)
    pristine=generated_dds((*VIOLET,128))
    if (payload==pristine or payload[:128]!=pristine[:128] or
        len(payload)!=len(pristine)):
        raise ValueError("Spatial DDS differs outside supported header contract")
    # Only the generated RGBA8 alpha bytes can change.
    diff=[i for i,(a,b) in enumerate(zip(payload,pristine)) if a!=b]
    expected_changes=WIDTH*WIDTH
    if (not diff or any(i<128 or (i-128)%4!=3 for i in diff)
        or len(diff)!=expected_changes):
        raise ValueError("Spatial DDS changed an unexpected source byte")
    root=Path(root)
    report=install_dynamic(root,shaders,"original")
    atlas=root/SUBDIR/ATLAS_NAME
    if atlas.is_symlink() or not atlas.is_file() or atlas.read_bytes()!=pristine:
        raise ValueError("Stage278 generated near DDS unexpectedly modified")
    atlas.write_bytes(payload)
    if atlas.read_bytes()!=payload:
        raise ValueError("Stage278 synthetic DDS write failed")
    report.update({
        "schema":SCHEMA,
        "scenario":case,
        "changed_file":ATLAS_NAME,
        "generated_only":True,
        "original_ps3_resources":False,
        "actual_gpu_render_verified":False,
        "near_dds_sha256":hashlib.sha256(payload).hexdigest(),
        "near_original_dds_sha256":hashlib.sha256(pristine).hexdigest(),
        "near_alpha_band_splits":list(BAND_SPLITS),
        "near_alpha_values":list(ALPHA_BANDS[case]),
        "near_texture_dimensions":[WIDTH,WIDTH],
        "expected_native_pass_order":[2,1,0],
        "expected_probe_rgb":{name:list(expected_at(case,name))
                              for name in PROBES},
    })
    return report


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--shaders",type=Path,required=True)
    p.add_argument("--case",choices=CASES,required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(install_masked(args.data_root,args.shaders,args.case),
                         sort_keys=True))
    except (OSError,ValueError) as exc:
        print("Stage278 four-band alpha generated DDS rejected: "+str(exc),
              file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
