#!/usr/bin/env python3
"""Prepare only GENERATED/USER-SUPPLIED UAM shaders for the GPU triangle NRO.

Source is a DKSH pair compiled by UAM; no PS3 material/model resources are
read or shipped. The resulting 'switch/foj/gpu' tree is copied to the user's
own SD card by the user. Never silently overwrite existing assets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.validate_dksh import DkshError, inspect_dksh

NATIVE_DKSH_CAPACITY = 126976
RELATIVE_FOLDER = Path("switch/foj/gpu")


def prepare_triangle_shaders(
    vertex: Path, fragment: Path, output_dir: Path,
) -> dict:
    vertex = Path(vertex)
    fragment = Path(fragment)
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or output_dir.is_symlink():
        raise ValueError("Output directory must exist and cannot be a symlink")

    payloads = []
    for shader, stage, target in (
        (vertex, "vertex", "foj_actor.vert.dksh"),
        (fragment, "fragment", "foj_triangle.frag.dksh"),
    ):
        length = shader.stat().st_size
        if not 256 <= length <= NATIVE_DKSH_CAPACITY:
            raise DkshError(f"{shader.name}: exceeds Switch shader slot")
        contents = shader.read_bytes()
        report = inspect_dksh(contents, expected_stage=stage)
        payloads.append((target, contents, report))

    folder = output_dir / RELATIVE_FOLDER
    destinations = [folder / name for name, _, _ in payloads]
    if any(p.exists() or p.is_symlink() for p in destinations):
        raise FileExistsError("Refusing to overwrite prepared GPU shader files")

    folder.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for path, (_, blob, _) in zip(destinations, payloads):
            with path.open("xb") as stream:
                created.append(path)
                stream.write(blob)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        raise

    return {
        "target_directory": str(RELATIVE_FOLDER),
        "shaders": [
            {"name": name, "stage": report["stages"][0], "bytes": len(blob)}
            for name, blob, report in payloads
        ],
        "note": (
            "Prepares generated shader assets only. No Nintendo Switch "
            "compilation, native draw call or physical GPU rendering "
            "has been verified by this operation."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vertex", type=Path)
    parser.add_argument("fragment", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = prepare_triangle_shaders(
            args.vertex, args.fragment, args.output_dir
        )
    except (ValueError, OSError) as exc:
        print(f"Shader preparation error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
