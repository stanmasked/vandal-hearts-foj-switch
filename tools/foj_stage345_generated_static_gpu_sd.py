#!/usr/bin/env python3
"""Generate a synthetic unskinned two-section/two-material bundle for NeXium.

Never accepts original assets or an existing private SD root. This fixture is
only for testing the static FOJRM001 path and the existing GPU material batches.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import struct
import sys

SCHEMA = "foj.stage345.generated_static_multimaterial_sd.v1"
SUBDIR = Path("sdmc/switch/foj/gpu")
COLORS = ((232, 55, 28, 255), (21, 202, 219, 255))
TRIS = (
    ((-.86, -.42, 0.), (-.03, -.42, 0.), (-.44, .64, 0.)),
    ((.03, -.42, .05), (.86, -.42, .05), (.44, .64, .05)),
)
SHADERS = ("foj_actor.vert.dksh", "foj_triangle.frag.dksh")


def generated_geometry() -> bytes:
    # FOJRM001 header + two section records + six unskinned vertices.
    buf = bytearray(28 + 2 * 8 + 6 * 76)
    buf[:8] = b"FOJRM001"
    struct.pack_into("<IIIII", buf, 8, 1, 0, 6, 2, 0)
    struct.pack_into("<IIII", buf, 28, 0, 3, 3, 3)
    for i, xyz in enumerate(vertex for tri in TRIS for vertex in tri):
        off = 44 + i * 76
        uv = ((0., 1.), (1., 1.), (.5, 0.))[i % 3]
        struct.pack_into("<8fI", buf, off, *xyz, *uv, 0., 0., 1., 0)
        for j in range(5):
            struct.pack_into("<If", buf, off + 36 + j * 8, 0, 0.)
    return bytes(buf)


def generated_materials() -> bytes:
    return b"FOJMAT01" + struct.pack("<IIII", 2, 2, 0, 1)


def generated_dds(color: tuple[int, int, int, int]) -> bytes:
    width = height = 64
    header = bytearray(128)
    header[:4] = b"DDS "
    for offset, value in (
        (4, 124), (8, 0x100F), (12, height), (16, width),
        (20, width * 4), (76, 32), (80, 0x41),
        (88, 32), (92, 0xFF), (96, 0xFF00),
        (100, 0xFF0000), (104, 0xFF000000), (108, 0x1000),
    ):
        struct.pack_into("<I", header, offset, value)
    return bytes(header) + bytes(color) * (width * height)


def install_generated(root: Path, shader_dir: Path) -> dict:
    root, shader_dir = Path(root), Path(shader_dir)
    if root.exists() or root.is_symlink():
        raise ValueError("Refusing an existing NeXium data root")
    if not root.parent.is_dir() or root.parent.is_symlink():
        raise ValueError("Generated root parent must be an ordinary directory")
    if shader_dir.is_symlink() or not shader_dir.is_dir():
        raise ValueError("Missing generated shader directory")
    shaders = [shader_dir / name for name in SHADERS]
    if any(p.is_symlink() or not p.is_file() or not 256 <= p.stat().st_size <= 126976
           for p in shaders):
        raise ValueError("Required generated UAM shaders absent or invalid-size")
    import tools.validate_dksh as dk
    dk.inspect_dksh(shaders[0].read_bytes(), expected_stage="vertex")
    dk.inspect_dksh(shaders[1].read_bytes(), expected_stage="fragment")
    root.mkdir(mode=0o700)
    try:
        output = root / SUBDIR
        output.mkdir(parents=True, mode=0o700)
        for name, data in (
            ("actor.fojrm", generated_geometry()),
            ("actor.fojmat", generated_materials()),
            ("material0.dds", generated_dds(COLORS[0])),
            ("material1.dds", generated_dds(COLORS[1])),
            (SHADERS[0], shaders[0].read_bytes()),
            (SHADERS[1], shaders[1].read_bytes()),
        ):
            with (output / name).open("xb") as dest:
                dest.write(data)
    except BaseException:
        shutil.rmtree(root)
        raise
    return {
        "schema": SCHEMA,
        "fixture": "invented_unskinned_two_section_two_material_mesh",
        "bone_count": 0,
        "vertex_count": 6,
        "section_count": 2,
        "batch_count": 2,
        "texture_count": 2,
        "texture_dimensions": [64, 64],
        "expected_material_rgba": [list(v) for v in COLORS],
        "sd_subdirectory": str(SUBDIR),
        "original_assets_loaded": False,
        "actual_neixum_render_verified": False,
        "physical_switch_verified": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--shaders", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = install_generated(args.data_root, args.shaders)
    except (OSError, ValueError) as exc:
        print("Generated-only static GPU SD setup rejected: " + type(exc).__name__,
              file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
