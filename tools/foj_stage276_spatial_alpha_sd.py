#!/usr/bin/env python3
"""Stage276: invented alpha-gradient step inside ONE generated RGBA8 DDS.

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

CASES=("alpha-left-clear","alpha-right-clear")
SCHEMA="foj.stage276.spatial_alpha_generated_dds.v1"
WIDTH=64
SPLIT_X=48
ATLAS_NAME="material0.dds"
PROBES={"left_overlap":(605,400),"right_overlap":(675,400),
        "rear_only":(760,400)}
EXPECTED_ALPHA={
    "alpha-left-clear":{"left_overlap":0,"right_overlap":128},
    "alpha-right-clear":{"left_overlap":128,"right_overlap":0},
}


def near_atlas(case:str)->bytes:
    if case not in CASES:
        raise ValueError("Unknown spatial-alpha case")
    data=bytearray(generated_dds((*VIOLET,128)))
    if len(data)!=128+WIDTH*WIDTH*4:
        raise ValueError("Generated DDS layout changed")
    for y in range(WIDTH):
        for x in range(WIDTH):
            clear=(x<SPLIT_X) if case=="alpha-left-clear" else (x>=SPLIT_X)
            data[128+4*(y*WIDTH+x)+3]=0 if clear else 128
    return bytes(data)


def target_rgb(alpha:int)->tuple[int,int,int]:
    if not isinstance(alpha,int) or alpha not in (0,128):
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
    return target_rgb(EXPECTED_ALPHA[case][probe])


def install_masked(root:Path,shaders:Path,case:str)->dict:
    if case not in CASES:
        raise ValueError("Unknown Stage276 case")
    payload=near_atlas(case)
    pristine=generated_dds((*VIOLET,128))
    if (payload==pristine or payload[:128]!=pristine[:128] or
        len(payload)!=len(pristine)):
        raise ValueError("Spatial DDS differs outside supported header contract")
    # Only the generated RGBA8 alpha bytes can change.
    diff=[i for i,(a,b) in enumerate(zip(payload,pristine)) if a!=b]
    if (not diff or any(i<128 or (i-128)%4!=3 for i in diff)
        or len(diff)!=SPLIT_X*WIDTH if case=="alpha-left-clear"
        else not diff or any(i<128 or (i-128)%4!=3 for i in diff)
        or len(diff)!=(WIDTH-SPLIT_X)*WIDTH):
        raise ValueError("Spatial DDS changed an unexpected source byte")
    root=Path(root)
    report=install_dynamic(root,shaders,"original")
    atlas=root/SUBDIR/ATLAS_NAME
    if atlas.is_symlink() or not atlas.is_file() or atlas.read_bytes()!=pristine:
        raise ValueError("Stage276 generated near DDS unexpectedly modified")
    atlas.write_bytes(payload)
    if atlas.read_bytes()!=payload:
        raise ValueError("Stage276 synthetic DDS write failed")
    report.update({
        "schema":SCHEMA,
        "scenario":case,
        "changed_file":ATLAS_NAME,
        "generated_only":True,
        "original_ps3_resources":False,
        "actual_gpu_render_verified":False,
        "near_dds_sha256":hashlib.sha256(payload).hexdigest(),
        "near_original_dds_sha256":hashlib.sha256(pristine).hexdigest(),
        "near_alpha_split_x":SPLIT_X,
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
        print("Stage276 spatial generated DDS rejected: "+str(exc),
              file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
