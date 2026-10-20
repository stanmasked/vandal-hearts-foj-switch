#!/usr/bin/env python3
"""Generate only invented 3-layer FOJRM001 actor, materials and RGBA8 DDS.

No input game files; independent output root must not already exist.
Layer order in actor sections is VIOLET near 0, WARM middle 1, COOL rear 2.
Stage267 submits these sections in reverse [2,1,0].
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import struct
import sys

from tools.foj_stage260_generated_gpu_sd import SUBDIR, generated_dds, install_generated
from tools.foj_stage266_transparency_order import COOL, WARM, VIOLET, Layer, composite_rgb, order_layers

SCHEMA = "foj.stage267.generated_three_layer.v1"
CASES = {
    "both-half": (128, 128),
    "no-middle": (128, 0),
    "no-near": (0, 128),
}
TRIANGLES = {
    "violet": ((-.76, -.50), (.34, -.50), (-.21, .69)),
    "warm": ((-.76, -.50), (.34, -.50), (-.21, .69)),
    "cool": ((-.35, -.50), (.75, -.50), (.20, .69)),
}
# Camera relative z; only the ordering matters after stream normalization.
DEPTHS = {"violet": .60, "warm": .08, "cool": -.55}
COLORS = {"violet": VIOLET, "warm": WARM, "cool": COOL}


def generated_three_layer_mesh() -> bytes:
    vertices = 9
    sections = 3
    off_vertices = 28 + 32 + 8 * sections
    buf = bytearray(off_vertices + 76 * vertices)
    buf[:8] = b"FOJRM001"
    struct.pack_into("<IIIII", buf, 8, 1, 1, vertices, sections, 0)
    struct.pack_into("<I", buf, 28, 0xFFFFFFFF)
    struct.pack_into("<f", buf, 44, 1.0)
    for slot in range(sections):
        struct.pack_into("<II", buf, 60 + 8 * slot, slot * 3, 3)
    for slot, name in enumerate(("violet", "warm", "cool")):
        for index, (x, y) in enumerate(TRIANGLES[name]):
            vertex = slot * 3 + index
            pos = off_vertices + 76 * vertex
            u,v = ((0., 1.),(1., 1.),(.5, 0.))[index]
            struct.pack_into("<8f", buf, pos, x, y, DEPTHS[name],
                             u, v, 0., 0., 1.)
            struct.pack_into("<II f", buf, pos + 32, 1, 0, 1.)
    return bytes(buf)


def generated_three_layer_materials() -> bytes:
    return b"FOJMAT01" + struct.pack("<IIIII", 3, 3, 0, 1, 2)


def expected_rgb(case: str) -> tuple[int, int, int]:
    if case not in CASES:
        raise ValueError("Invalid synthetic scene")
    near_alpha, mid_alpha = CASES[case]
    layers = (
        Layer("violet", .85, (*VIOLET, near_alpha), "translucent_front"),
        Layer("cool", .20, (*COOL, 255), "opaque_rear"),
        Layer("warm", .55, (*WARM, mid_alpha), "translucent_front"),
    )
    return composite_rgb(order_layers(layers))


def install_three_layer(root: Path, shaders: Path, case: str) -> dict:
    if case not in CASES:
        raise ValueError("Unknown synthetic alpha case")
    root = Path(root)
    receipt = install_generated(root, Path(shaders))
    near_alpha, mid_alpha = CASES[case]
    dest = root / SUBDIR
    try:
        files = {
            "actor.fojrm": generated_three_layer_mesh(),
            "actor.fojmat": generated_three_layer_materials(),
            "material0.dds": generated_dds((*VIOLET, near_alpha)),
            "material1.dds": generated_dds((*WARM, mid_alpha)),
            "material2.dds": generated_dds((*COOL, 255)),
        }
        for name, payload in files.items():
            path = dest / name
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise ValueError("Unexpected generated file kind")
            if name == "material2.dds":
                with path.open("xb") as output:
                    output.write(payload)
            else:
                path.write_bytes(payload)
    except BaseException:
        shutil.rmtree(root)
        raise
    receipt.update({
        "schema": SCHEMA, "case": case, "vertex_count": 9,
        "batch_count": 3, "texture_count": 3,
        "draw_order": ["cool", "warm", "violet"],
        "alpha_near": near_alpha, "alpha_middle": mid_alpha,
        "expected_overlap_rgb": list(expected_rgb(case)),
        "generated_only": True,
        "original_foj_resources": False,
        "actual_gpu_render_verified": False,
    })
    return receipt


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--shaders", type=Path, required=True)
    p.add_argument("--scenario", choices=tuple(CASES), required=True)
    args = p.parse_args(argv)
    try:
        receipt = install_three_layer(args.data_root, args.shaders, args.scenario)
    except (ValueError, OSError) as exc:
        p.error("Invented three-layer fixture refused: " + str(exc))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
