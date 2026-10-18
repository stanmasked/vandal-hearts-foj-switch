#!/usr/bin/env python3
"""Private-only intake preflight for FOJRM001 and one/two BANIM assets.

No game resource bytes, paths, bone arrays, exact transforms, filenames
or content hashes are emitted. Hierarchy match is NOT original-game actor
association proof. Do not upload protected assets or private reports.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.check_local_rig_pair import inspect_pair, MAX_RIG_FILE, MAX_ANIM_FILE

SCHEMA = "foj.stage194.private_clip_set.v1"


def inspect_clip_set(rig: bytes, primary: bytes,
                     secondary: bytes | None = None) -> dict:
    first = inspect_pair(rig, primary)
    if secondary is not None:
        if secondary == primary:
            raise ValueError("Second animation must be distinct")
        second = inspect_pair(rig, secondary)
        if second["bone_count"] != first["bone_count"]:
            raise ValueError("Clip bone counts differ")
    else:
        second = None

    # Deliberately OMIT sampled poses and their coordinates, arbitrary user
    # local file paths, game names, keyframe arrays and file hashes.
    return {
        "schema": SCHEMA,
        "private_intake_only": True,
        "rig_format": "FOJRM001",
        "vertex_count": first["vertex_count"],
        "bone_count": first["bone_count"],
        "root_count": first["root_bone_count"],
        "primary_track_count": first["animation_tracks"],
        "secondary_track_count": second["animation_tracks"] if second else None,
        "primary_hierarchy_match": first["complete_parent_hierarchy_match"],
        "secondary_hierarchy_match":
            second["complete_parent_hierarchy_match"] if second else None,
        "optional_secondary_accepted": second is not None,
        "original_ps3_actor_clip_binding_verified": False,
        "original_ps3_skin_transform_verified": False,
        "original_ps3_animation_scheduler_verified": False,
        "physical_nintendo_switch_execution_verified": False,
    }


def bounded_read(path: Path, limit: int) -> bytes:
    size = path.stat().st_size
    if size <= 0 or size > limit:
        raise ValueError("File size outside bounded input contract")
    with path.open("rb") as file:
        content = file.read(limit + 1)
    if len(content) != size or len(content) > limit:
        raise ValueError("File changed or exceeded bounded read limit")
    return content


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rig", type=Path)
    parser.add_argument("primary", type=Path)
    parser.add_argument("--secondary", type=Path)
    args = parser.parse_args(argv)
    try:
        rig = bounded_read(args.rig, MAX_RIG_FILE)
        primary = bounded_read(args.primary, MAX_ANIM_FILE)
        secondary = (bounded_read(args.secondary, MAX_ANIM_FILE)
                     if args.secondary is not None else None)
        result = inspect_clip_set(rig, primary, secondary)
    except (OSError, ValueError):
        # Never echo an input filename, parser context or asset-derived field.
        print("Private FOJ rig/clip intake rejected; inspect locally.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
