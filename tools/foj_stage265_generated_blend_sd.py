#!/usr/bin/env python3
"""Generate invented near/front RGBA DDS blending against opaque cool depth.

Use the exact Stage263 FOJRM geometry and local-only source intake; both
overlapping triangles share deterministic RGB and Z, and only warm texture
alpha changes. Cases are 0, 128 and 255 / 255, never user-owned assets.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys
from tools.foj_stage263_generated_depth_sd import install_depth
from tools.foj_stage260_generated_gpu_sd import SUBDIR, COLORS, generated_dds

SCHEMA="foj.stage265.generated_alpha_blend.v1"
ALPHAS={"clear":0,"half":128,"solid":255}


def make_warm_dds(case:str)->bytes:
    if case not in ALPHAS: raise ValueError("Invalid alpha scenario")
    warm=COLORS[0]
    return generated_dds((warm[0],warm[1],warm[2],ALPHAS[case]))


def install_blend(root:Path,shaders:Path,case:str)->dict:
    if case not in ALPHAS:
        raise ValueError("Unsupported blend scenario")
    report=install_depth(root,shaders,"warm")
    try:
        warm=root/SUBDIR/"material0.dds"
        if warm.is_symlink() or not warm.is_file():
            raise ValueError("Generated warm texture missing")
        warm.write_bytes(make_warm_dds(case))
    except BaseException:
        shutil.rmtree(root)
        raise
    report.update({
        "schema":SCHEMA,
        "scenario":case,
        "warm_front_alpha":ALPHAS[case],
        "fixed_draw_order":["cool_opaque_rear","warm_front_alpha"],
        "front_depth_write":False,
        "rear_depth_write":True,
        "fixture":"invented_near_front_blended_over_opaque_far",
        "original_foj_resources":False,
        "actual_gpu_test_verified":False,
        "physical_switch_verified":False,
    })
    return report


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--shaders",type=Path,required=True)
    p.add_argument("--scenario",choices=tuple(ALPHAS),required=True)
    a=p.parse_args(argv)
    try:out=install_blend(a.data_root,a.shaders,a.scenario)
    except (OSError,ValueError) as exc:
        print("Generated-only blend SD rejected: "+type(exc).__name__,file=sys.stderr)
        return 2
    print(json.dumps(out,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
