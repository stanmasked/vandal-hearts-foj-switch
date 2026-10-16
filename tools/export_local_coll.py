#!/usr/bin/env python3
"""Explicit local-only export of ONE COLL file from user's own PS3 package.

The output contains proprietary game bytes and MUST NOT be committed or
redistributed. The project builds never run this tool, and no output is
created unless the user passes --output. No overwriting existing files.
This export uses the already tested PS3 debug-PKG + PSARC stream readers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.inspect_debug_pkg_assets import (
    DebugPKG, FormatError, PSARC, unpack_stored_zip,
)
from tools.inspect_map_coll import (
    MapFormatError, summarize_collision, validate_map_name,
)
from tools.inspect_split_pkg import JoinedParts

MAX_COLL_BYTES = 1048576


def local_export(
    parts: list[str | Path], map_name: str, output: str | Path
) -> dict:
    """Write a single user's-owned map file, exclusively to requested path."""
    validate_map_name(map_name)
    destination = Path(output)
    if destination.suffix.lower() != ".coll":
        raise ValueError("Only .coll output is supported")
    if not destination.parent.is_dir():
        raise ValueError("Output directory must already exist")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Output exists; refusing to overwrite original bytes")

    with JoinedParts(parts) as joined:
        begin, length = unpack_stored_zip(joined)
        pkg = DebugPKG(joined, begin, length)
        matching = [
            item for item in pkg.items()
            if item["path"].lower() == "usrdir/cdata.psarc"
        ]
        if len(matching) != 1:
            raise FormatError("Expected one USRDIR/cdata.psarc")
        archive_item = matching[0]
        archive = PSARC(pkg, archive_item["offset"], archive_item["size"])
        paths = archive.manifest()
        name = f"data/maps/{map_name}.coll"
        if paths.count(name) != 1:
            raise FormatError("Requested COLL file is missing or ambiguous")
        index = paths.index(name) + 1
        resource = archive.entry_data(index, limit=MAX_COLL_BYTES)
        summary = summarize_collision(resource)

    # File is output only after the full syntax and schema check succeeds.
    with destination.open("xb") as output_file:
        output_file.write(resource)
    return {
        "local_file": destination.name,
        "bytes_written": len(resource),
        "grid_width": summary["width"],
        "grid_height": summary["height"],
        "warning": "Copyrighted local asset. Do not upload to GitHub.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path,
                        help="Original .pkg.zip.001, .pkg.zip.002 in byte order")
    parser.add_argument("--map", default="map1-1",
                        help="Map identifier (default map1-1)")
    parser.add_argument("--output", type=Path, required=True,
                        help="Explicit locally controlled .coll output path")
    args = parser.parse_args(argv)
    try:
        result = local_export(args.parts, args.map, args.output)
    except (FormatError, MapFormatError, ValueError, OSError) as exc:
        print(f"Local COLL export error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
