#!/usr/bin/env python3
"""Reproducible, aggregate-only FoJ rig/BANIM audit from user-local PKG.

Never writes copyrighted models, animation keys, game binaries or decrypted
resources. All decoding is bounded and runs in memory. Reports counts and
validation invariants, not original transforms.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Iterable

from tools.decode_rig_banim import parse_banim, parse_bmodel_rig
from tools.inspect_complete_bmodel import decode_model


def audit_rig_animation_records(
    model_payloads: Iterable[bytes],
    animation_payloads: Iterable[bytes],
) -> dict:
    counts: Counter[str] = Counter()
    rig_metadata: Counter[str] = Counter()
    model_rig_roots: Counter[str] = Counter()

    for data in model_payloads:
        model = decode_model(data)
        footer = data[-model.footer_bytes:]
        rig = parse_bmodel_rig(footer)
        counts["models"] += 1
        if rig.bones:
            counts["models_with_bones"] += 1
            counts["bones"] += len(rig.bones)
            roots = sum(b.parent is None for b in rig.bones)
            model_rig_roots[str(roots)] += 1
            for bone in rig.bones:
                rig_metadata[str(bone.metadata)] += 1
        if any(shape.influences_per_vertex for shape in model.shapes):
            counts["models_with_weighted_vertices"] += 1

    tracks_per_clip: Counter[str] = Counter()
    zero_duration = 0
    for payload in animation_payloads:
        clip = parse_banim(payload, retain_keys=False)
        counts["animations"] += 1
        counts["tracks"] += len(clip.tracks)
        counts["keyframes"] += clip.key_count
        tracks_per_clip[str(len(clip.tracks))] += 1
        if clip.duration == 0:
            zero_duration += 1

    return {
        "bmodel_file_count": counts["models"],
        "models_with_rig": counts["models_with_bones"],
        "models_with_skin_weights": counts["models_with_weighted_vertices"],
        "total_bones": counts["bones"],
        "bone_metadata_field_counts": dict(sorted(rig_metadata.items())),
        "rig_root_counts_by_model": dict(sorted(model_rig_roots.items())),
        "banim_file_count": counts["animations"],
        "banim_track_count": counts["tracks"],
        "banim_total_keyframes": counts["keyframes"],
        "zero_duration_clips": zero_duration,
        "track_count_distribution": dict(sorted(tracks_per_clip.items(),
                                                key=lambda x: int(x[0]))),
        "limitations": [
            "Static rig hierarchy and local-keyframe attributes only.",
            "No game-engine skin matrices, animation blending or final render verified.",
            "No source animation coordinates or protected bytes included.",
        ],
    }


def audit_split_game(parts: list[Path]) -> dict:
    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip,
    )
    from tools.inspect_split_pkg import JoinedParts

    with JoinedParts(parts) as stream:
        offset, length = unpack_stored_zip(stream)
        package = DebugPKG(stream, offset, length)
        items = [x for x in package.items()
                 if x["path"].lower() == "usrdir/cdata.psarc"]
        if len(items) != 1:
            raise FormatError("Missing/ambiguous USRDIR/cdata.psarc")
        arc = PSARC(package, items[0]["offset"], items[0]["size"])
        files = arc.manifest()
        models = [i+1 for i, name in enumerate(files)
                  if name.lower().endswith(".bmodel")]
        clips = [i+1 for i, name in enumerate(files)
                 if name.lower().endswith(".banim")]
        if len(models) > 2000 or len(clips) > 2000:
            raise FormatError("Unexpected asset count exceeds safety limit")

        def get_records(indices):
            for i in indices:
                yield arc.entry_data(i, limit=4_000_000)

        return audit_rig_animation_records(get_records(models),
                                           get_records(clips))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path,
                        help="User-provided ordered PS3 ZIP fragments")
    args = parser.parse_args(argv)
    try:
        report = audit_split_game(args.parts)
    except (ValueError, OSError) as exc:
        print(f"Rig/animation audit error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
