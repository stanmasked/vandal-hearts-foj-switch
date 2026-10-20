#!/usr/bin/env python3
"""Invented four-quadrant RGBA DDS atlases for actual Stage262 GPU UV proof.

The two distinguishable warm/cool materials retain the Stage260 color family
so that the existing independent pixel/geometry gates still apply. Individual
quadrants detect swapped U, flipped V, wrong material and constant UV.
No private or original FoJ file is accepted or copied.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys

from tools.foj_stage260_generated_gpu_sd import (
    SUBDIR, install_generated, generated_dds
)

SCHEMA="foj.stage262.generated_gpu_uv.v1"
QUADRANTS=("top_left","top_right","bottom_left","bottom_right")
PALETTES={
    "warm":(
        (234,45,35,255), (250,130,22,255),
        (180,20,42,255), (225,90,90,255),
    ),
    "cool":(
        (15,165,237,255), (85,220,211,255),
        (26,190,165,255), (75,175,247,255),
    ),
}


def quadrant_dds(colors:tuple) -> bytes:
    if len(colors)!=4 or any(len(c)!=4 or any(not 0<=v<=255 for v in c)
                              for c in colors):
        raise ValueError("Four valid opaque RGBA quadrants required")
    if any(c[3]!=255 for c in colors):
        raise ValueError("No alpha transparency in geometry/UV test")
    base=bytearray(generated_dds(colors[0]))
    width=height=64
    for y in range(height):
        for x in range(width):
            index=(2 if y>=32 else 0)+(1 if x>=32 else 0)
            pos=128+4*(y*width+x)
            base[pos:pos+4]=bytes(colors[index])
    return bytes(base)


def install_quadrants(root:Path,shaders:Path)->dict:
    receipt=install_generated(root,shaders)
    try:
        dst=root/SUBDIR
        for index,name in enumerate(("warm","cool")):
            filename=dst/f"material{index}.dds"
            if not filename.is_file() or filename.is_symlink():
                raise ValueError("Generated DDS file changed before replacement")
            filename.write_bytes(quadrant_dds(PALETTES[name]))
    except BaseException:
        shutil.rmtree(root)
        raise
    receipt.update({
        "schema":SCHEMA,
        "fixture":"two_triangles_eight_unique_uv_quadrant_colors",
        "expected_material_rgba":None,
        "material_quadrant_rgba":{n:[list(c) for c in colors]
                                   for n,colors in PALETTES.items()},
        "quadrant_order":list(QUADRANTS),
        "expected_uv_v_zero":"top_of_decoded_dds",
        "actual_neixum_render_verified":False,
        "original_foj_resource_verified":False,
    })
    return receipt


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--shaders",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        receipt=install_quadrants(args.data_root,args.shaders)
    except (OSError,ValueError) as exc:
        print("Generated GPU UV fixture rejected: "+type(exc).__name__,
              file=sys.stderr)
        return 2
    print(json.dumps(receipt,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
