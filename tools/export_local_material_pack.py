#!/usr/bin/env python3
"""Export a user-owned FoJ model's complete per-section DDS material bundle.

The proprietary PS3 data are read only from the caller's local NPEB00148
archive. Nothing is uploaded. Output is NEW preview.fojmat + texture_XX.tga
files in a caller-chosen existing directory; no file is overwritten.

FOJMAT01 is our little-endian research-only section -> texture mapping,
not a format shipped with the PS3 game. It supports max 8 unique atlases.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

from tools.inspect_complete_bmodel import decode_model, resolve_textures
from tools.export_local_texture import validate_legacy_dds

MAGIC = b"FOJMAT01"
MAX_ATLASES = 8
MAX_SECTIONS = 64
MAX_DDS_BYTES = 8 * 1024 * 1024


def make_material_plan(model_bytes: bytes, name: str,
                       manifest: list[str]) -> tuple[bytes, list[str]]:
    """Produce deterministic safe mapping, no commercial texture pixels."""
    model = decode_model(model_bytes)
    if not 1 <= len(model.shapes) <= MAX_SECTIONS:
        raise ValueError("Too many model shape sections")
    matches = resolve_textures(name, model.materials, manifest)
    paths: list[str] = []
    slots: list[int] = []
    for shape in model.shapes:
        links = matches.get(shape.material)
        if links is None or len(links) != 1:
            raise ValueError(f"Ambiguous/non-single texture for material {shape.material!r}")
        link = links[0]
        selected = link["path"]
        if selected is None:
            raise ValueError(f"Texture path unresolved for material {shape.material!r}")
        if selected not in paths:
            paths.append(selected)
        if len(paths) > MAX_ATLASES:
            raise ValueError("More than 8 unique textures: not supported yet")
        slots.append(paths.index(selected))
    payload = MAGIC + struct.pack("<II", len(slots), len(paths))
    payload += struct.pack("<" + "I" * len(slots), *slots)
    return payload, paths


def export_local_material_pack(parts: list[Path], asset: str,
                               output_dir: Path) -> dict:
    if (not asset.startswith("data/") or
        not asset.lower().endswith(".bmodel") or
        "\\" in asset or ".." in asset.split("/")):
        raise ValueError("Unsafe model path")
    if not output_dir.is_dir() or output_dir.is_symlink():
        raise ValueError("Output directory must exist, and cannot be symlink")
    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip
    )
    from tools.inspect_split_pkg import JoinedParts

    with JoinedParts(parts) as stream:
        offset, length = unpack_stored_zip(stream)
        package = DebugPKG(stream, offset, length)
        package_items = [x for x in package.items()
                         if x["path"].lower() == "usrdir/cdata.psarc"]
        if len(package_items) != 1:
            raise FormatError("Expected one cdata.psarc")
        item = package_items[0]
        archive = PSARC(package, item["offset"], item["size"])
        manifest = archive.manifest()
        if manifest.count(asset) != 1:
            raise FormatError("Requested BMODEL is missing or duplicated")
        model_data = archive.entry_data(manifest.index(asset) + 1,
                                        limit=4_000_000)
        mapping, resource_paths = make_material_plan(model_data, asset,
                                                       manifest)
        filenames = ["preview.fojmat"] + [
            f"texture_{i:02d}.tga" for i in range(len(resource_paths))
        ]
        destinations = [output_dir / name for name in filenames]
        if any(path.exists() or path.is_symlink() for path in destinations):
            raise FileExistsError("Material pack file already exists")
        textures: list[bytes] = []
        stats = []
        for name in resource_paths:
            raw = archive.entry_data(manifest.index(name) + 1,
                                     limit=MAX_DDS_BYTES)
            info = validate_legacy_dds(raw)
            textures.append(raw)
            stats.append({
                "asset": name,
                "width": info["width"],
                "height": info["height"],
                "format": info["format"]
            })

    # All formats and paths checked before the first file is written.
    created: list[Path] = []
    try:
        for path, payload in zip(destinations, [mapping] + textures):
            with path.open("xb") as fp:
                created.append(path)
                fp.write(payload)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return {
        "model": asset,
        "section_count": struct.unpack_from("<I", mapping, 8)[0],
        "unique_texture_count": len(resource_paths),
        "local_files": filenames,
        "local_textures": stats,
        "warning": "Keep all original model/texture data on private user storage."
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path)
    parser.add_argument("--asset", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = export_local_material_pack(args.parts, args.asset,
                                            args.output_dir)
    except (OSError, ValueError) as exc:
        print(f"FoJ material pack error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
