#!/usr/bin/env python3
"""Pack fixed, generated-only research GPU assets for a *manual* Switch test.

Inputs are the exact locally built NRO/DKSH paths (not PS3 source data).
Bundle contents are fixed; never scan directories or accept game files.
The ZIP is newly created and reproducible from identical build inputs.
This cannot launch a console, verify homebrew runtime, or validate gameplay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

from tools.foj_stage162_synthetic_dds import generated_dds
from tools.validate_dksh import inspect_dksh
from tools.validate_nro import validate_nro

MAX_NRO_BYTES = 16 * 1024 * 1024
ZIP_PREFIX = "switch/foj/"
# The name before "|" is relative to the repository, not a user path.
INPUTS = (
    ("build/foj-deko3d-clear-smoke.nro", "foj-deko3d-clear-smoke.nro", "nro"),
    ("build/foj-deko3d-triangle-research.nro",
     "foj-deko3d-triangle-research.nro", "nro"),
    ("gpu/build/foj_actor.vert.dksh", "gpu/foj_actor.vert.dksh", "vertex"),
    ("gpu/build/foj_triangle.frag.dksh",
     "gpu/foj_triangle.frag.dksh", "fragment"),
)
GUIDE = """FoJ Stage 165 — GENERATED-ONLY GPU DDS smoke test
NOT A PLAYABLE GAME. NOT TESTED ON PHYSICAL NINTENDO SWITCH.

This bundle contains two SDK-built research NROs, two UAM-generated
DKSH shaders, and two invented 8x8 DDS checkerboard textures.
NO original Flames of Judgment PS3 resources, gameplay or models.

Copy the CONTENTS OF 'switch/' to the root of your own authorized
homebrew Nintendo Switch SD card (not the switch folder twice).
Start the clear-smoke NRO, then triangle-research NRO via Homebrew Menu.

DDS status color screens use 120 presented frames for material0 and
120 for material1: green=CPU DDS decoded, blue=optional DDS missing,
amber=invalid DDS, magenta=unsafe path, orange=source changed,
red=I/O error. A DDS error holds the screen and returns nonzero.
On two valid generated DDS files expect green then green followed by
two colored checkerboard quads. Exit via Plus after visible frames.

Run the full manual A-E test plan at:
https://github.com/stanmasked/vandal-hearts-foj-switch/blob/main/docs/GPU_STAGE162_SD_SMOKE.md

Switch screen presentation, hardware input, resource loading and
shutdown behavior have NOT been verified by CI. Do not upload any
user-owned PS3 files, texture dumps or private paths to GitHub.
"""


def _source_bytes(path: Path, kind: str) -> bytes:
    try:
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode):
            raise ValueError("Missing or unsafe fixed research build input")
        cap = MAX_NRO_BYTES if kind == "nro" else 8 * 1024 * 1024
        if not 0 < meta.st_size <= cap:
            raise ValueError("Research build input outside size bound")
        with path.open("rb") as stream:
            data = stream.read(cap + 1)
        if len(data) != meta.st_size:
            raise ValueError("Research build input changed during read")
    except OSError:
        raise ValueError("Missing or unreadable fixed research build input") from None
    if kind == "nro":
        validate_nro(data)
    else:
        inspect_dksh(data, expected_stage=kind)
    return data


def contents(root: Path) -> tuple[dict[str, bytes], dict]:
    if not isinstance(root, Path):
        raise ValueError("Research root must be a Path")
    files: dict[str, bytes] = {}
    for relative, staged, kind in INPUTS:
        files[ZIP_PREFIX + staged] = _source_bytes(root / relative, kind)
    for material in range(2):
        files[ZIP_PREFIX + f"gpu/material{material}.dds"] = generated_dds(material)
    files["README_STAGE165.txt"] = GUIDE.encode("utf-8")
    manifest = {
        "schema": "foj-stage165-generated-gpu-sd-bundle-v1",
        "provenance": "generated-research-assets-only",
        "files": [{
            "sd_relative_path": name,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        } for name, data in sorted(files.items())],
        "ps3_assets_included": False,
        "switch_hardware_tested": False,
        "playable_game": False,
    }
    files["MANIFEST_STAGE165.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n").encode("utf-8")
    return files, manifest


def publish_bundle(root: Path, destination: Path) -> dict:
    if not isinstance(destination, Path):
        raise ValueError("Archive target must be a Path")
    payload, manifest = contents(root)  # Validate everything BEFORE output.
    try:
        with destination.open("xb") as output:
            with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_STORED,
                                 allowZip64=False) as archive:
                for name, data in sorted(payload.items()):
                    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_STORED
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, data)
    except FileExistsError:
        raise ValueError("Bundle archive output must be new") from None
    except OSError:
        raise ValueError("Unable to write local research ZIP bundle") from None
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True,
                        help="New .zip archive, refuses overwrite")
    args = parser.parse_args()
    try:
        manifest = publish_bundle(args.repo_root, args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print("Stage 165 generated-only GPU SD smoke ZIP ready:",
          len(manifest["files"]), "files; hardware test NOT performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
