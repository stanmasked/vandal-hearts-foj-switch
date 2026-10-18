#!/usr/bin/env python3
"""Aggregate-only BMODEL skeleton vs BANIM parent-topology candidate audit.

Reads a user-owned FoJ debug-style PS3 package *locally*. Reports only
aggregated candidate counts; NEVER writes original geometry, motion,
paths, track hierarchies, filenames, fingerprints, or extracted bytes.

Exact topology agreement is a necessary structural test for the present
rigged-actor viewer, NOT proof of original animation/model identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Iterable

from tools.decode_rig_banim import parse_banim, parse_bmodel_rig
from tools.inspect_complete_bmodel import decode_model, MAX_MODEL_BYTES

SCHEMA = "foj-stage188-private-topology-candidates-v1"
MAX_MODELS = 2000
MAX_ANIMATIONS = 2000
MAX_ANIM_BYTES = 16_000_000
MAX_RIG_BONES = 256
MAX_PAIR_CANDIDATES = MAX_MODELS * MAX_ANIMATIONS

Topology = tuple[int, ...]


def _skeleton_topology(payload: bytes) -> Topology | None:
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_MODEL_BYTES:
        raise ValueError("Invalid or oversized private BMODEL")
    model = decode_model(payload)
    if model.footer_bytes <= 0 or model.footer_bytes > len(payload):
        raise ValueError("Invalid BMODEL skeleton footer bounds")
    rig = parse_bmodel_rig(payload[-model.footer_bytes:])
    if not rig.bones:
        return None
    if len(rig.bones) > MAX_RIG_BONES:
        raise ValueError("Unsupported number of model bones")
    return tuple(-1 if bone.parent is None else bone.parent for bone in rig.bones)


def _animation_topology(payload: bytes) -> Topology:
    if not isinstance(payload, bytes) or not 17 <= len(payload) <= MAX_ANIM_BYTES:
        raise ValueError("Invalid or oversized private BANIM")
    animation = parse_banim(payload, retain_keys=False)
    return tuple(-1 if track.parent is None else track.parent
                 for track in animation.tracks)


def audit_topology_records(
    models: Iterable[bytes], animations: Iterable[bytes]
) -> dict:
    rig_counts: Counter[Topology] = Counter()
    clip_counts: Counter[Topology] = Counter()
    model_count = 0
    clip_count = 0
    unrigged_count = 0
    for model in models:
        model_count += 1
        if model_count > MAX_MODELS:
            raise ValueError("Private BMODEL count exceeds safety limit")
        topology = _skeleton_topology(model)
        if topology is None:
            unrigged_count += 1
        else:
            rig_counts[topology] += 1

    for animation in animations:
        clip_count += 1
        if clip_count > MAX_ANIMATIONS:
            raise ValueError("Private BANIM count exceeds safety limit")
        clip_counts[_animation_topology(animation)] += 1

    matching = rig_counts.keys() & clip_counts.keys()
    total_pairs = sum(rig_counts[key] * clip_counts[key] for key in matching)
    if total_pairs > MAX_PAIR_CANDIDATES:
        raise ValueError("Too many possible candidate combinations")
    matching_models = sum(rig_counts[key] for key in matching)
    matching_clips = sum(clip_counts[key] for key in matching)
    one_to_one_classes = sum(rig_counts[key] == clip_counts[key] == 1
                             for key in matching)
    ambiguous_classes = sum(
        rig_counts[key] > 1 or clip_counts[key] > 1 for key in matching)
    ambiguous_pairs = sum(
        rig_counts[key] * clip_counts[key]
        for key in matching if rig_counts[key] > 1 or clip_counts[key] > 1
    )

    model_by_bones: Counter[int] = Counter()
    clip_by_tracks: Counter[int] = Counter()
    for key, count in rig_counts.items():
        model_by_bones[len(key)] += count
    for key, count in clip_counts.items():
        clip_by_tracks[len(key)] += count
    same_count_pairs = sum(
        model_by_bones[count] * clip_by_tracks[count]
        for count in model_by_bones.keys() & clip_by_tracks.keys()
    )
    if total_pairs > same_count_pairs:
        raise AssertionError("Full-parent topology cannot exceed bone-count candidates")

    # Counts only. Never return even a salted digest of a source topology:
    # many small hierarchy shapes are too easy to enumerate.
    return {
        "schema": SCHEMA,
        "provenance": "user-local-private-resources-aggregate-only",
        "bmodel_records_checked": model_count,
        "bmodel_rigged": model_count - unrigged_count,
        "bmodel_without_rig": unrigged_count,
        "banim_records_checked": clip_count,
        "distinct_model_hierarchy_shapes": len(rig_counts),
        "distinct_animation_hierarchy_shapes": len(clip_counts),
        "same_bone_track_count_candidate_pairs": same_count_pairs,
        "exact_parent_topology_candidate_pairs": total_pairs,
        "candidate_pairs_rejected_by_parent_topology":
            same_count_pairs - total_pairs,
        "model_records_with_at_least_one_topology_candidate": matching_models,
        "animation_records_with_at_least_one_topology_candidate": matching_clips,
        "rigged_models_without_topology_candidate":
            model_count - unrigged_count - matching_models,
        "animations_without_topology_candidate": clip_count - matching_clips,
        "matching_hierarchy_shape_classes": len(matching),
        "unique_one_model_one_animation_shape_classes": one_to_one_classes,
        "ambiguous_hierarchy_shape_classes": ambiguous_classes,
        "candidate_pairs_in_ambiguous_classes": ambiguous_pairs,
        "asset_names_published": False,
        "parent_index_arrays_published": False,
        "original_asset_bytes_exported": False,
        "engine_binding_verified": False,
        "retargeting_verified": False,
        "physical_switch_execution_verified": False,
        "note": (
            "Structural candidate counts only. Hierarchy equality cannot "
            "identify actual BMODEL/BANIM pairing, coordinate conventions, "
            "rest-pose correction, blending, or original-engine playback."
        ),
    }


def audit_split_game(parts: list[Path]) -> dict:
    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip
    )
    from tools.inspect_split_pkg import JoinedParts

    if not parts or len(parts) > 8:
        raise ValueError("Supply ordered private split archive parts")
    with JoinedParts(parts) as stream:
        start, length = unpack_stored_zip(stream)
        package = DebugPKG(stream, start, length)
        items = [item for item in package.items()
                 if item["path"].lower() == "usrdir/cdata.psarc"]
        if len(items) != 1:
            raise FormatError("Expected one private game PSARC")
        entry = items[0]
        archive = PSARC(package, entry["offset"], entry["size"])
        manifest = archive.manifest()
        model_ids = [i + 1 for i, name in enumerate(manifest)
                     if name.lower().endswith(".bmodel")]
        anim_ids = [i + 1 for i, name in enumerate(manifest)
                    if name.lower().endswith(".banim")]
        if len(model_ids) > MAX_MODELS or len(anim_ids) > MAX_ANIMATIONS:
            raise FormatError("Unreasonable private asset count")

        def private_records(ids: list[int], limit: int):
            for index in ids:
                yield archive.entry_data(index, limit=limit)

        return audit_topology_records(
            private_records(model_ids, MAX_MODEL_BYTES),
            private_records(anim_ids, MAX_ANIM_BYTES)
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path,
                        help="Ordered PRIVATE PS3 .pkg.zip.001/.002 parts")
    args = parser.parse_args(argv)
    try:
        result = audit_split_game(args.parts)
    except (ValueError, OSError) as error:
        # Deliberately do not print errors that might disclose filenames,
        # protected archive paths or sensitive input properties.
        print("Private BMODEL/BANIM topology audit did not validate",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
