#!/usr/bin/env python3
"""Stage287: only invented local FOJRM/FOJMAT/DDS for actual host C loader.

The fixture's three textures and actor are deterministic public research
constants; it has no game input, network code, PKG access or real shaders.
It is not accepted as evidence of PS3 asset format or actual GPU rendering.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys

from tools.foj_stage267_generated_multiblend_sd import (
    generated_three_layer_mesh, generated_three_layer_materials,
)
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET, WARM, COOL

FILES = {
    "actor.fojrm": generated_three_layer_mesh(),
    "actor.fojmat": generated_three_layer_materials(),
    "material0.dds": generated_dds((*VIOLET, 128)),
    "material1.dds": generated_dds((*WARM, 128)),
    "material2.dds": generated_dds((*COOL, 255)),
}


def create(root: Path) -> None:
    root = Path(root)
    if (root.exists() or root.is_symlink() or not root.parent.is_dir()
            or root.parent.is_symlink()):
        raise ValueError("Stage287 output must be a new ordinary local directory")
    root.mkdir(mode=0o700)
    try:
        for name, data in FILES.items():
            handle = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(handle, "wb") as stream:
                    handle = -1
                    stream.write(data)
            finally:
                if handle >= 0:
                    os.close(handle)
    except BaseException:
        shutil.rmtree(root)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        create(args.output_root)
    except (OSError, ValueError):
        print("Stage287 generated host fixture refused", file=sys.stderr)
        return 2
    print("STAGE287_GENERATED_ONLY_HOST_FIXTURE_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
