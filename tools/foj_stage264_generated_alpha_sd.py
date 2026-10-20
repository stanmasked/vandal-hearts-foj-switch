#!/usr/bin/env python3
"""Only invented SD data: near warm triangle with alpha-cutout DDS aperture.

Compare aperture-vs-opaque with same geometry and shaders. User-owned PS3
model, artwork, SD paths or screenshots are never read. The original generated
Stage263 model draws warm first/cool second: with a near warm quad, only real
fragment discard can expose the farther blue object at the cutout center.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys

from tools.foj_stage263_generated_depth_sd import install_depth
from tools.foj_stage260_generated_gpu_sd import SUBDIR, generated_dds, COLORS
from tools.validate_dksh import inspect_dksh

SCHEMA="foj.stage264.generated_alpha_cutout.v1"
HOLE_U=(.62,.77)
HOLE_V=(.59,.80)
# Interior probes are several pixels away from hole edges and triangles.
PROBES={
    "masked_overlap":(640,400),
    "opaque_overlap":(600,400),
    "warm_wing":(520,380),
    "cool_wing":(760,400),
}


def masked_dds(masked:bool)->bytes:
    rgba=COLORS[0]
    result=bytearray(generated_dds(rgba))
    if masked:
        for y in range(64):
            for x in range(64):
                u=(x+.5)/64
                v=(y+.5)/64
                if HOLE_U[0]<=u<=HOLE_U[1] and HOLE_V[0]<=v<=HOLE_V[1]:
                    result[128+4*(y*64+x)+3]=0
    return bytes(result)


def install_alpha(root:Path,shader_dir:Path,scenario:str)->dict:
    if scenario not in ("masked","opaque"):
        raise ValueError("Only masked/opaque generated scenarios allowed")
    fragment=shader_dir/"foj_alpha_cutout.frag.dksh"
    if fragment.is_symlink() or not fragment.is_file() or not 256<=fragment.stat().st_size<=126976:
        raise ValueError("Required independently compiled alpha shader missing")
    shader=fragment.read_bytes()
    inspect_dksh(shader,expected_stage="fragment")
    report=install_depth(root,shader_dir,"warm")
    try:
        sd=root/SUBDIR
        frag=sd/"foj_alpha_cutout.frag.dksh"
        if frag.exists() or frag.is_symlink():
            raise ValueError("Refusing overwrite of shader")
        with frag.open("xb") as f:
            f.write(shader)
        target=sd/"material0.dds"
        if not target.is_file() or target.is_symlink():
            raise ValueError("Invented DDS unexpectedly missing")
        target.write_bytes(masked_dds(scenario=="masked"))
    except BaseException:
        shutil.rmtree(root)
        raise
    report.update({
        "schema":SCHEMA,
        "fixture":"invented_near_first_rgba_alpha_aperture",
        "scenario":scenario,
        "hole_uv":{"u":list(HOLE_U),"v":list(HOLE_V)},
        "probes":{key:list(val) for key,val in PROBES.items()},
        "fragment":"generated_UAM_foj_alpha_cutout.frag.dksh",
        "gpu_guest_verified":False,
        "original_foj_resources":False,
    })
    return report


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--shaders",type=Path,required=True)
    p.add_argument("--scenario",required=True,choices=("masked","opaque"))
    a=p.parse_args(argv)
    try:
        record=install_alpha(a.data_root,a.shaders,a.scenario)
    except (OSError,ValueError) as exc:
        print("Stage264 generated-only input rejected: "+type(exc).__name__,file=sys.stderr)
        return 2
    print(json.dumps(record,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
