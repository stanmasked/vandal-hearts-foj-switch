#!/usr/bin/env python3
"""Audit structural BMODEL rig/BANIM compatibility in a user-local PS3 archive.

Matches bone-count AND every hierarchical parent index. The output contains
only statistics and names of unmatched clips, never game motion or mesh bytes.
Equal hierarchy is necessary, NOT sufficient, for correct character animation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from tools.decode_rig_banim import parse_banim, parse_bmodel_rig
from tools.inspect_complete_bmodel import decode_model

MAX_FILES_PER_TYPE = 2000
ParentTuple = tuple[int, ...]


def rig_parent_layout(data: bytes) -> ParentTuple:
    model = decode_model(data)
    rig = parse_bmodel_rig(data[-model.footer_bytes:])
    return tuple(-1 if b.parent is None else b.parent for b in rig.bones)


def clip_parent_layout(data: bytes) -> ParentTuple:
    clip = parse_banim(data)
    return tuple(-1 if t.parent is None else t.parent for t in clip.tracks)


def compare_layouts(
    model_layouts: dict[str, ParentTuple],
    clip_layouts: dict[str, ParentTuple],
) -> dict:
    if (len(model_layouts) > MAX_FILES_PER_TYPE or
        len(clip_layouts) > MAX_FILES_PER_TYPE):
        raise ValueError("Rig/clip comparison exceeds safety limits")
    model_groups: dict[ParentTuple, list[str]] = defaultdict(list)
    clip_groups: dict[ParentTuple, list[str]] = defaultdict(list)
    for name, layout in model_layouts.items():
        if layout:
            model_groups[layout].append(name)
    for name, layout in clip_layouts.items():
        if layout:
            clip_groups[layout].append(name)

    matched = model_groups.keys() & clip_groups.keys()
    matched_model_count = sum(len(model_groups[layout]) for layout in matched)
    matched_clip_count = sum(len(clip_groups[layout]) for layout in matched)
    candidate_pairs = sum(
        len(model_groups[layout]) * len(clip_groups[layout])
        for layout in matched
    )
    unmatched = sorted(
        (name for layout, filenames in clip_groups.items()
         if layout not in model_groups for name in filenames)
    )
    return {
        "rigged_models": sum(map(len, model_groups.values())),
        "nonempty_clips": sum(map(len, clip_groups.values())),
        "models_with_matching_clip_hierarchy": matched_model_count,
        "clips_with_matching_model_hierarchy": matched_clip_count,
        "distinct_matching_parent_hierarchies": len(matched),
        "candidate_model_clip_pairs": candidate_pairs,
        "unmatched_clip_names": unmatched,
        "unmatched_clip_track_counts": {
            name: len(clip_layouts[name]) for name in unmatched
        },
        "model_bone_count_distribution": dict(sorted(
            Counter({n: sum(len(files) for layout, files in model_groups.items()
                            if len(layout) == n)
                     for n in {len(layout) for layout in model_groups}}).items()
        )),
        "note": (
            "Parent-array match is structural only, not proof of intended "
            "asset association, bind-pose compatibility or original-game "
            "animation behavior."
        ),
    }


def compare_local_game(parts: list[Path]) -> dict:
    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip,
    )
    from tools.inspect_split_pkg import JoinedParts
    with JoinedParts(parts) as stream:
        offset, length = unpack_stored_zip(stream)
        package = DebugPKG(stream, offset, length)
        matches = [
            item for item in package.items()
            if item["path"].lower() == "usrdir/cdata.psarc"
        ]
        if len(matches) != 1:
            raise FormatError("Expected exactly one FoJ cdata.psarc")
        item = matches[0]
        arc = PSARC(package, item["offset"], item["size"])
        names = arc.manifest()
        models = [(name, i + 1) for i, name in enumerate(names)
                  if name.lower().endswith(".bmodel")]
        clips = [(name, i + 1) for i, name in enumerate(names)
                 if name.lower().endswith(".banim")]
        if (len(models) > MAX_FILES_PER_TYPE or
            len(clips) > MAX_FILES_PER_TYPE):
            raise ValueError("Unexpected game asset count")
        model_layouts = {
            name: rig_parent_layout(arc.entry_data(index, limit=4_000_000))
            for name, index in models
        }
        clip_layouts = {
            name: clip_parent_layout(arc.entry_data(index, limit=8_000_000))
            for name, index in clips
        }
        return compare_layouts(model_layouts, clip_layouts)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path,
                        help="User-local PS3 split ZIP pieces in byte order")
    args = parser.parse_args(argv)
    try:
        result = compare_local_game(args.parts)
    except (ValueError, OSError) as exc:
        print(f"Rig hierarchy audit error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
