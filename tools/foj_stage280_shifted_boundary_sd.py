#!/usr/bin/env python3
"""Stage280 generated-only DDS with the 0/255 alpha edge moved in U."""
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
    COOL,VIOLET,WARM,Layer,order_layers,composite_rgb,
)

SCHEMA="foj.stage280.shifted_boundary_dds.v1"
SPLITS={"edge-u40":40,"edge-u52":52}
CASES=tuple(SPLITS)
WIDTH=64
PROFILE_Y=440
FRAME_CROSSINGS={"edge-u40":618,"edge-u52":680}
LEFT_CONTROL_OFFSET=-13
RIGHT_CONTROL_OFFSET=13
ATLAS_NAME="material0.dds"


def positions(case:str)->dict[str,tuple[int,int]]:
    if case not in CASES:
        raise ValueError("Unrecognized Stage280 case")
    center=FRAME_CROSSINGS[case]
    return {
        "left_control":(center+LEFT_CONTROL_OFFSET,PROFILE_Y),
        "right_control":(center+RIGHT_CONTROL_OFFSET,PROFILE_Y),
        "rear_only":(760,400),
    }


def profile_x(case:str)->tuple[int,...]:
    center=FRAME_CROSSINGS[case] if case in CASES else None
    if center is None: raise ValueError("Unrecognized Stage280 case")
    return tuple(range(center-13,center+14))


def near_atlas(case:str)->bytes:
    if case not in CASES: raise ValueError("Unrecognized Stage280 DDS case")
    buf=bytearray(generated_dds((*VIOLET,128)))
    if len(buf)!=128+WIDTH*WIDTH*4: raise ValueError("Unexpected DDS fixture size")
    for y in range(WIDTH):
        for x in range(WIDTH):
            buf[128+(y*WIDTH+x)*4+3]=0 if x<SPLITS[case] else 255
    return bytes(buf)


def target_rgb(alpha:int)->tuple[int,int,int]:
    if type(alpha) is not int or alpha not in (0,255):
        raise ValueError("Unsupported Stage280 alpha")
    return composite_rgb(order_layers((
        Layer("rear",.20,(*COOL,255),"opaque_rear"),
        Layer("middle",.55,(*WARM,128),"translucent_front"),
        Layer("near",.85,(*VIOLET,alpha),"translucent_front"),
    )))


def expected_at(case:str,label:str)->tuple[int,int,int]:
    if label not in positions(case): raise ValueError("Unknown Stage280 pixel probe")
    if label=="rear_only": return COOL
    return target_rgb(0 if label=="left_control" else 255)


def install_masked(root:Path,shaders:Path,case:str)->dict:
    if case not in CASES: raise ValueError("Unknown Stage280 generated case")
    atlas=near_atlas(case)
    base=generated_dds((*VIOLET,128))
    if (len(atlas)!=len(base) or atlas[:128]!=base[:128] or
        any(a!=b for i,(a,b) in enumerate(zip(atlas,base))
            if i>=128 and (i-128)%4!=3) or
        sum(a!=b for a,b in zip(atlas,base))!=WIDTH*WIDTH):
        raise ValueError("Stage280 changed non-alpha or missing DDS bytes")
    root=Path(root)
    receipt=install_dynamic(root,shaders,"original")
    path=root/SUBDIR/ATLAS_NAME
    if path.is_symlink() or not path.is_file() or path.read_bytes()!=base:
        raise ValueError("Unexpected previously modified DDS")
    path.write_bytes(atlas)
    if path.read_bytes()!=atlas:
        raise ValueError("Stage280 DDS write failed")
    receipt.update({
        "schema":SCHEMA,"scenario":case,
        "generated_only":True,"original_ps3_resources":False,
        "actual_gpu_render_verified":False,"changed_file":ATLAS_NAME,
        "near_original_dds_sha256":hashlib.sha256(base).hexdigest(),
        "near_dds_sha256":hashlib.sha256(atlas).hexdigest(),
        "near_alpha_split_x":SPLITS[case],
        "expected_half_transition_x":FRAME_CROSSINGS[case],
        "near_texture_dimensions":[WIDTH,WIDTH],
        "profile_x_positions":list(profile_x(case)),
        "profile_y":PROFILE_Y,
        "profile_goal":"verify UV-driven shift, never infer sampler mode",
        "expected_native_pass_order":[2,1,0],
        "expected_probe_rgb":{
            name:list(expected_at(case,name)) for name in positions(case)
        },
    })
    return receipt


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",required=True,type=Path)
    p.add_argument("--shaders",required=True,type=Path)
    p.add_argument("--case",choices=CASES,required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(
            install_masked(args.data_root,args.shaders,args.case),sort_keys=True))
    except (OSError,ValueError) as e:
        print("Stage280 generated DDS rejected: "+str(e),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
