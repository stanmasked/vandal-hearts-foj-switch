#!/usr/bin/env python3
"""Build only invented overlapping FOJRM001 actors to prove deko3d depth.

The actor always has two ordered draw batches (warm material 0 first, cool
material 1 second). A pair of independent guest runs reverses which batch
is nearer. This forces a real Z-buffer for the warm-near case: without
depth testing, the cool second draw would incorrectly cover the center.
No original PS3 assets or user-supplied paths are read by this generator.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import struct
import sys

from tools.foj_stage260_generated_gpu_sd import SUBDIR,install_generated

SCHEMA="foj.stage263.generated_depth.v1"
TRIANGLES={
    "warm": ((-.68,-.50),(.42,-.50),(-.13,.69)),
    "cool": ((-.43,-.50),(.67,-.50),(.12,.69)),
}
NEAR_Z=.35
FAR_Z=-.35
PROBES={
    "warm_only":(520,380),
    "overlap":(640,400),
    "cool_only":(760,400),
}


def overlap_mesh(near:str)->bytes:
    if near not in TRIANGLES:
        raise ValueError("near must be warm or cool")
    # Retain the Stage260 research FOJRM001 exact binary contract and
    # generated identity root bone/2 contiguous material sections.
    from tools.foj_stage260_generated_gpu_sd import generated_geometry
    buf=bytearray(generated_geometry())
    for material,tri in TRIANGLES.items():
        start=0 if material=="warm" else 3
        z=NEAR_Z if material==near else FAR_Z
        for idx,(x,y) in enumerate(tri):
            struct.pack_into("<fff",buf,76+76*(start+idx),x,y,z)
    return bytes(buf)


def install_depth(root:Path,shaders:Path,near:str)->dict:
    if near not in TRIANGLES:
        raise ValueError("unsupported depth scenario")
    report=install_generated(root,shaders)
    try:
        path=root/SUBDIR/"actor.fojrm"
        if path.is_symlink() or not path.is_file():
            raise ValueError("generated actor path changed unexpectedly")
        path.write_bytes(overlap_mesh(near))
    except BaseException:
        shutil.rmtree(root)
        raise
    report.update({
        "schema":SCHEMA,
        "fixture":"invented_overlapping_triangles_with_ordered_materials",
        "near_material":near,
        "draw_order":["warm","cool"],
        "near_camera_z":NEAR_Z,
        "far_camera_z":FAR_Z,
        "reference_probes":{key:list(value) for key,value in PROBES.items()},
        "physical_switch_verified":False,
        "original_ps3_assets_loaded":False,
        "actual_neixum_render_verified":False,
    })
    return report


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--shaders",type=Path,required=True)
    p.add_argument("--near",choices=("warm","cool"),required=True)
    args=p.parse_args(argv)
    try:
        receipt=install_depth(args.data_root,args.shaders,args.near)
    except (OSError,ValueError) as exc:
        print("Depth fixture rejected: "+type(exc).__name__,file=sys.stderr)
        return 2
    print(json.dumps(receipt,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
