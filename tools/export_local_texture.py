#!/usr/bin/env python3
"""Opt-in, local-only export of ONE DDS-in-.tga texture from user's PS3 backup.

This tool reads user's non-finalized PKG and cdata.psarc, validates a DDS
header and copies only the selected file to an explicitly specified local
path. No automatic GitHub upload, no key material, no redistribution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

from tools.inspect_debug_pkg_assets import (
    DebugPKG, FormatError, PSARC, unpack_stored_zip,
)
from tools.inspect_split_pkg import JoinedParts

MAX_TEXTURE_BYTES = 8 * 1024 * 1024


def validate_legacy_dds(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise FormatError("Resource is not a complete legacy DDS header")
    size, height, width = struct.unpack_from("<III", data, 4)
    # Read width and height from their actual DDS offsets: 16 and 12.
    height, width = struct.unpack_from("<II", data, 12)
    pf_size, pf_flags, fourcc, depth = struct.unpack_from("<IIII", data, 76)
    if size != 124 or pf_size != 32 or not (1 <= height <= 4096 and 1 <= width <= 4096):
        raise FormatError("Malformed or unsupported DDS header/dimensions")
    if pf_flags & 0x4:
        if fourcc != 0x31545844:
            raise FormatError("Only DXT1 texture export supported")
        fmt = "DXT1"
        required = ((width + 3) // 4) * ((height + 3) // 4) * 8
    else:
        red, green, blue, alpha = struct.unpack_from("<IIII", data, 92)
        if not (pf_flags & 0x41) == 0x41 or depth != 32 or (
            red, green, blue, alpha
        ) != (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000):
            raise FormatError("Only BGRA8 texture export supported")
        fmt = "BGRA8"
        required = width * height * 4
    if len(data) - 128 < required:
        raise FormatError("Truncated DDS payload")
    return {"width": width, "height": height, "format": fmt}


def export_local_texture(
    parts: list[str | Path],
    member_name: str,
    output: str | Path,
) -> dict:
    if (not member_name.startswith("data/") or
        not member_name.lower().endswith((".tga", ".dds")) or
        "\\" in member_name or
        ".." in member_name.split("/")):
        raise ValueError("Only safe in-archive DDS/.tga texture paths supported")
    destination = Path(output)
    if destination.suffix.lower() not in (".tga", ".dds"):
        raise ValueError("Output suffix must be .tga or .dds")
    if not destination.parent.is_dir():
        raise ValueError("Output directory must exist")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Output exists; refusing overwrite")

    with JoinedParts(parts) as joined:
        start, pkg_length = unpack_stored_zip(joined)
        pkg = DebugPKG(joined, start, pkg_length)
        items = [x for x in pkg.items()
                 if x["path"].lower() == "usrdir/cdata.psarc"]
        if len(items) != 1:
            raise FormatError("Exactly one PSARC required")
        arc = PSARC(pkg, items[0]["offset"], items[0]["size"])
        filenames = arc.manifest()
        if filenames.count(member_name) != 1:
            raise FormatError("Texture filename not found or ambiguous")
        index = filenames.index(member_name) + 1
        texture = arc.entry_data(index, limit=MAX_TEXTURE_BYTES)
        info = validate_legacy_dds(texture)

    with destination.open("xb") as stream:
        stream.write(texture)
    return {
        "filename": destination.name,
        "bytes_written": len(texture),
        **info,
        "notice": "Local-only user-provided game asset: do not redistribute.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path,
                        help="Ordered pieces of user's split ZIP")
    parser.add_argument("--asset", required=True,
                        help="Exact in-PSARC filename, e.g. data/actors/npc/avatar_texture.tga")
    parser.add_argument("--output", required=True, type=Path,
                        help="Explicit local filename; no overwrite")
    args = parser.parse_args(argv)
    try:
        result = export_local_texture(args.parts, args.asset, args.output)
    except (FormatError, OSError, ValueError) as exc:
        print(f"Texture export error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
