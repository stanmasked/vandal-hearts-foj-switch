#!/usr/bin/env python3
"""Explicit, local-only export of ONE original FoJ BANIM from user's PS3 ZIP.

Reads non-finalized user-controlled PS3 PKG -> cdata.psarc, verifies the
original BANIM structure, and only writes to a NEW path explicitly selected
by the user. Does not upload or publish proprietary animation data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.decode_rig_banim import parse_banim
from tools.inspect_debug_pkg_assets import (
    DebugPKG, FormatError, PSARC, unpack_stored_zip,
)
from tools.inspect_split_pkg import JoinedParts

MAX_LOCAL_CLIP = 8_000_000


def export_local_banim(parts: list[Path], asset: str,
                       destination: Path) -> dict:
    if (not asset.startswith("data/") or
        not asset.lower().endswith(".banim") or
        ".." in asset.split("/") or "\\" in asset):
        raise ValueError("Invalid BANIM asset path")
    if (destination.suffix.lower() != ".banim" or
        not destination.parent.is_dir()):
        raise ValueError("Output must be a .banim in an existing directory")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Refusing to overwrite existing local file")

    with JoinedParts(parts) as joined:
        start, size = unpack_stored_zip(joined)
        package = DebugPKG(joined, start, size)
        matches = [item for item in package.items()
                   if item["path"].lower() == "usrdir/cdata.psarc"]
        if len(matches) != 1:
            raise FormatError("Missing or ambiguous game PSARC")
        archive = PSARC(package, matches[0]["offset"], matches[0]["size"])
        names = archive.manifest()
        if names.count(asset) != 1:
            raise FormatError("Selected BANIM not found uniquely")
        content = archive.entry_data(names.index(asset) + 1,
                                     limit=MAX_LOCAL_CLIP)
        clip = parse_banim(content)
    with destination.open("xb") as output:
        output.write(content)
    return {
        "filename": destination.name,
        "bytes_written": len(content),
        "duration": clip.duration,
        "tracks": len(clip.tracks),
        "keys": clip.key_count,
        "notice": "Private user-owned animation. Never upload original asset.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path,
                        help="User-local PKG ZIP pieces, in byte order")
    parser.add_argument("--asset", required=True, help="Exact PSARC .banim path")
    parser.add_argument("--output", required=True, type=Path,
                        help="New, explicitly selected local .banim path")
    args = parser.parse_args(argv)
    try:
        report = export_local_banim(args.parts, args.asset, args.output)
    except (OSError, ValueError) as exc:
        print(f"BANIM local export error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
