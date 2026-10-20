#!/usr/bin/env python3
"""Stage271 invented *negative* actor fixture for guarded native NRO.

Unlike Stage269, this intentionally writes rejected geometry to a new
generated-only SD root. Never accepts existing roots or user assets.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

from tools.foj_stage267_generated_multiblend_sd import (
    install_three_layer, generated_three_layer_mesh, SUBDIR,
)
from tools.foj_stage269_guarded_scene import guard_three_layer_mesh
from tools.foj_stage268_transparency_crossing import UnsafeTransparencyOrder

CASES = ("crossing","reversed","coplanar")
VERTEX_OFFSET = 28+32+3*8
VERTEX_SIZE=76

def rejected_actor(kind: str) -> bytes:
    if kind not in CASES:
        raise ValueError("Unknown generated negative case")
    buf=bytearray(generated_three_layer_mesh())
    # Material 0 violet normally has z .60 and material 1 warm .08.
    # All share same projected XY triangle in the NRO's yaw=0 camera.
    # None of these three cases can obey fixed GPU draw order [2,1,0].
    if kind=="crossing":
        material, depths=1,(.90,-.10,.08)
    elif kind=="reversed":
        material, depths=0,(-.20,-.20,-.20)
    else:
        material, depths=1,(.60,.60,.60)
    for i,z in enumerate(depths):
        struct.pack_into("<f",buf,VERTEX_OFFSET+(3*material+i)*VERTEX_SIZE+8,z)
    candidate=bytes(buf)
    try:
        guard_three_layer_mesh(candidate)
    except UnsafeTransparencyOrder:
        return candidate
    raise AssertionError("Negative fixture unexpectedly passed host guard")

def install_rejected(root: Path,shaders: Path,kind: str)->dict:
    if kind not in CASES:
        raise ValueError("Unsupported generated negative case")
    # install_three_layer validates that root does not exist and shaders
    # are generated UAM modules. No user/private content is ever accepted.
    report=install_three_layer(root,shaders,"both-half")
    mesh=root/SUBDIR/"actor.fojrm"
    if mesh.is_symlink() or not mesh.is_file():
        raise ValueError("Generated mesh path is unsafe")
    mesh.write_bytes(rejected_actor(kind))
    receipt=root/SUBDIR/"foj-native-unsafe-reject.txt"
    if receipt.exists() or receipt.is_symlink():
        raise ValueError("Rejection receipt pre-exists")
    report.update({
        "schema":"foj.stage271.negative_generated_actor.v1",
        "negative_case":kind,
        "expected_native_exit_code":8,
        "expected_receipt":"FOJ_NATIVE_UNSAFE_REJECT_V1 exit=8 pre_gpu=1",
        "native_gpu_boot_claimed":False,
        "guest_execution_verified":False,
        "generated_only":True,
    })
    return report

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",required=True,type=Path)
    p.add_argument("--shaders",required=True,type=Path)
    p.add_argument("--case",required=True,choices=CASES)
    args=p.parse_args(argv)
    try:
        print(json.dumps(install_rejected(args.data_root,args.shaders,args.case),sort_keys=True))
    except (OSError,ValueError,AssertionError) as exc:
        print(type(exc).__name__+": "+str(exc),file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
