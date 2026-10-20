#!/usr/bin/env python3
"""Stage273 generated-only safe input-order reversal for a *real* NRO.

Unlike the Stage271 unsafe/crossing cases, both fixtures are strictly
sortable by the Stage272 geometry DAG; GPU draw order must adapt to Z.
No original game files or user data are loaded.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

from tools.foj_stage267_generated_multiblend_sd import (
    DEPTHS, SUBDIR, generated_three_layer_mesh, install_three_layer,
)
from tools.foj_stage266_transparency_order import (
    COOL, WARM, VIOLET, Layer, order_layers, composite_rgb,
)
from tools.foj_stage268_transparency_crossing import Triangle, plan_back_to_front

SCHEMA="foj.stage273.dynamic_gpu_sort.v1"
CASES=("original","reversed")
VERTEX_START=28+32+3*8
VERTEX_STRIDE=76
SECTIONS=("violet","warm","cool")
BACK_TO_FRONT={"original":(2,1,0),"reversed":(2,0,1)}


def generated_actor(case:str)->bytes:
    if case not in CASES:
        raise ValueError("Invalid generated scene type")
    data=bytearray(generated_three_layer_mesh())
    if case=="reversed":
        for index in range(3):
            near=VERTEX_START+index*VERTEX_STRIDE+8
            mid=VERTEX_START+(3+index)*VERTEX_STRIDE+8
            near_z=struct.unpack_from("<f",data,near)[0]
            mid_z=struct.unpack_from("<f",data,mid)[0]
            struct.pack_into("<f",data,near,mid_z)
            struct.pack_into("<f",data,mid,near_z)
    return bytes(data)


def safe_draw_order(mesh:bytes)->tuple[int,...]:
    if len(mesh)!=VERTEX_START+9*VERTEX_STRIDE or mesh[:8]!=b"FOJRM001":
        raise ValueError("Invalid complete generated actor")
    triangles=[]
    for section,name in enumerate(SECTIONS):
        vertices=[]
        for i in range(3):
            x,y,z=struct.unpack_from("<3f",mesh,VERTEX_START+
                                      (3*section+i)*VERTEX_STRIDE)
            vertices.append((float(x),float(y),float(z)))
        triangles.append((name,vertices))
    depth=[z for _,vs in triangles for _,_,z in vs]
    lo,hi=min(depth),max(depth)
    if not hi>lo:
        raise ValueError("No depth span")
    normalized=tuple(Triangle(name,tuple(
        (x,y,.01+.98*(z-lo)/(hi-lo)) for x,y,z in vs))
        for name,vs in triangles)
    return tuple(SECTIONS.index(name) for name in plan_back_to_front(normalized))


def expected_rgb(case:str)->tuple[int,int,int]:
    if case not in CASES:
        raise ValueError("Invalid scenario")
    near_z,mid_z=(.85,.55) if case=="original" else (.55,.85)
    return composite_rgb(order_layers((
        Layer("cool",.20,(*COOL,255),"opaque_rear"),
        Layer("violet",near_z,(*VIOLET,128),"translucent_front"),
        Layer("warm",mid_z,(*WARM,128),"translucent_front"),
    )))


def install_dynamic(root:Path,shaders:Path,case:str)->dict:
    if case not in CASES:
        raise ValueError("Unknown dynamic input case")
    root=Path(root)
    if root.exists() or root.is_symlink():
        raise ValueError("Refusing nonempty or existing SD root")
    actor=generated_actor(case)
    order=safe_draw_order(actor)
    if order!=BACK_TO_FRONT[case] or order[0]!=2:
        raise ValueError("Generated scene not safe for opaque-first rendering")
    report=install_three_layer(root,shaders,"both-half")
    mesh=root/SUBDIR/"actor.fojrm"
    if mesh.is_symlink() or not mesh.is_file():
        raise ValueError("Unexpected generated actor file")
    mesh.write_bytes(actor)
    report.update({
        "schema":SCHEMA,
        "scenario":case,
        "expected_native_pass_order":list(order),
        "expected_overlap_rgb":list(expected_rgb(case)),
        "expected_opaque_rear_first":True,
        "generated_only":True,
        "original_ps3_resources":False,
        "guest_proof_claimed":False,
    })
    return report


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root",required=True,type=Path)
    parser.add_argument("--shaders",required=True,type=Path)
    parser.add_argument("--scenario",required=True,choices=CASES)
    args=parser.parse_args(argv)
    try:
        print(json.dumps(install_dynamic(args.data_root,args.shaders,args.scenario),
                         sort_keys=True))
    except (OSError,ValueError) as exc:
        print("Stage273 fixture rejected: "+str(exc),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
