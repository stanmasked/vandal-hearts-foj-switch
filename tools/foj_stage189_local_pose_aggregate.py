#!/usr/bin/env python3
"""Private BMODEL bind / BANIM time-zero local-pose diagnostic (aggregate only).

The Stage 188 ordered-parent-topology test is required BEFORE computing
numerical differences. Even very small bind/clip local-pose differences
are not proof of original engine asset identity or correct skinning.

Never print/export original names, asset paths, transform values, topology
arrays, copyrighted geometry or raw BANIM keyframes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys
from typing import Iterable

from tools.decode_rig_banim import (
    parse_banim, parse_bmodel_rig, sample_local_pose
)
from tools.foj_stage188_private_topology_audit import (
    MAX_MODELS, MAX_ANIMATIONS, MAX_ANIM_BYTES, MAX_RIG_BONES,
    MAX_PAIR_CANDIDATES,
)
from tools.inspect_complete_bmodel import decode_model, MAX_MODEL_BYTES

SCHEMA = "foj-stage189-private-local-pose-distance-aggregates-v1"
MAX_EXAMINED_PAIRS = 250_000
TRANSLATION_CUTOFFS = (0.01, 0.1, 1.0, 10.0)
ROTATION_CUTOFFS = (0.0001, 0.01, 0.1)
TOPOLOGY = tuple[int, ...]
# Value is (quaternion XYZW, translation XYZ), both local floats.
POSE = tuple[tuple[tuple[float, ...], tuple[float, ...]], ...]


def _read_model(payload: bytes) -> tuple[TOPOLOGY, POSE] | None:
    if not isinstance(payload, bytes) or not 1 <= len(payload) <= MAX_MODEL_BYTES:
        raise ValueError("Invalid size of private BMODEL")
    model = decode_model(payload)
    if not 1 <= model.footer_bytes <= len(payload):
        raise ValueError("BMODEL footer outside file")
    skeleton = parse_bmodel_rig(payload[-model.footer_bytes:])
    if not skeleton.bones:
        return None
    if len(skeleton.bones) > MAX_RIG_BONES:
        raise ValueError("Too many bones")
    parents = tuple(-1 if bone.parent is None else bone.parent
                    for bone in skeleton.bones)
    poses = tuple((bone.rotation_xyzw, bone.translation_xyz)
                  for bone in skeleton.bones)
    return parents, poses


def _normalized_abs_dot(q1: tuple[float, ...],
                        q2: tuple[float, ...]) -> float:
    norm1 = math.sqrt(sum(x * x for x in q1))
    norm2 = math.sqrt(sum(x * x for x in q2))
    if norm1 < 0.001 or norm2 < 0.001:
        raise ValueError("Invalid source quaternion")
    dot = abs(sum(a * b for a, b in zip(q1, q2))) / (norm1 * norm2)
    return max(0.0, min(1.0, dot))


def _distance(model_pose: POSE, animation_pose: POSE) -> tuple[float, float]:
    if not model_pose or len(model_pose) != len(animation_pose):
        raise ValueError("Mismatched local-pose lengths")
    squared_translation = 0.0
    sum_rotation = 0.0
    for (bind_q, bind_t), (clip_q, clip_t) in zip(
        model_pose, animation_pose, strict=True
    ):
        squared_translation += sum((a - b) ** 2 for a, b
                                   in zip(bind_t, clip_t, strict=True))
        sum_rotation += 1 - _normalized_abs_dot(bind_q, clip_q)
    return (math.sqrt(squared_translation / len(model_pose)),
            sum_rotation / len(model_pose))


def audit_pose_records(
    model_payloads: Iterable[bytes], animation_payloads: Iterable[bytes]
) -> dict:
    # Store only one bounded bind pose per BMODEL. BANIM keys are retained
    # only for the clip currently being checked, never across the archive.
    rigs: dict[TOPOLOGY, list[POSE]] = defaultdict(list)
    models = unrigged = animations = rigged_models = 0
    for payload in model_payloads:
        models += 1
        if models > MAX_MODELS:
            raise ValueError("Too many BMODEL records")
        item = _read_model(payload)
        if item is None:
            unrigged += 1
            continue
        topology, poses = item
        rigs[topology].append(poses)
        rigged_models += 1

    matching_clips = 0
    topology_pairs = 0
    evaluated = 0
    sample_time = 0.0
    translation_counts = Counter({c: 0 for c in TRANSLATION_CUTOFFS})
    rotation_counts = Counter({c: 0 for c in ROTATION_CUTOFFS})
    both_near = 0
    min_translation = math.inf
    max_translation = 0.0
    min_rotation = math.inf
    max_rotation = 0.0

    for payload in animation_payloads:
        animations += 1
        if animations > MAX_ANIMATIONS:
            raise ValueError("Too many BANIM records")
        if not isinstance(payload, bytes) or not 17 <= len(payload) <= MAX_ANIM_BYTES:
            raise ValueError("Invalid size of private BANIM")
        clip = parse_banim(payload, retain_keys=True)
        topology = tuple(-1 if track.parent is None else track.parent
                         for track in clip.tracks)
        candidates = rigs.get(topology, ())
        if not candidates:
            continue
        matching_clips += 1
        topology_pairs += len(candidates)
        if topology_pairs > MAX_PAIR_CANDIDATES or (
            topology_pairs > MAX_EXAMINED_PAIRS
        ):
            raise ValueError("Too many candidate pose comparisons")

        sampled = sample_local_pose(clip, sample_time)
        local_pose = tuple((key.rotation_xyzw, key.translation_xyz)
                           for key in sampled)
        for model_pose in candidates:
            dist, rot = _distance(model_pose, local_pose)
            evaluated += 1
            min_translation = min(dist, min_translation)
            max_translation = max(dist, max_translation)
            min_rotation = min(rot, min_rotation)
            max_rotation = max(rot, max_rotation)
            for threshold in TRANSLATION_CUTOFFS:
                if dist <= threshold:
                    translation_counts[threshold] += 1
            for threshold in ROTATION_CUTOFFS:
                if rot <= threshold:
                    rotation_counts[threshold] += 1
            if dist <= 1.0 and rot <= 0.01:
                both_near += 1

    if evaluated != topology_pairs:
        raise AssertionError("Incomplete candidate comparisons")
    # For a NO-MATCH case, range endpoints remain null, not NaN/Infinity.
    return {
        "schema": SCHEMA,
        "provenance": "user-local-private-resources-aggregate-only",
        "bmodels_checked": models,
        "models_with_rigs": rigged_models,
        "models_without_rigs": unrigged,
        "banims_checked": animations,
        "banims_with_topology_candidates": matching_clips,
        "exact_parent_topology_pairs_examined": evaluated,
        "sample_time_seconds": sample_time,
        "translation_metric": "root_mean_square_local_XYZ_offset_in_source_units",
        "translation_pairs_below_cumulative_cutoffs": {
            str(c): translation_counts[c] for c in TRANSLATION_CUTOFFS
        },
        "rotation_metric": "mean_1_minus_absolute_normalized_quaternion_dot",
        "rotation_pairs_below_cumulative_cutoffs": {
            str(c): rotation_counts[c] for c in ROTATION_CUTOFFS
        },
        "pairs_near_both_at_translation_1_rotation_0_01": both_near,
        "observed_translation_rms_min": (round(min_translation, 6)
                                         if evaluated else None),
        "observed_translation_rms_max": (round(max_translation, 6)
                                         if evaluated else None),
        "observed_rotation_dissimilarity_min": (round(min_rotation, 8)
                                                if evaluated else None),
        "observed_rotation_dissimilarity_max": (round(max_rotation, 8)
                                                if evaluated else None),
        "local_coordinate_spaces_confirmed_comparable": False,
        "bind_pose_math_verified_against_original_engine": False,
        "authentic_model_animation_identity_verified": False,
        "asset_names_published": False,
        "per_bone_transforms_published": False,
        "original_game_bytes_exported": False,
        "physical_switch_runtime_verified": False,
        "note": (
            "Numeric differences are exploratory and measured in unverified "
            "coordinate spaces. A small distance is NOT evidence of a true "
            "model-animation pair; a large one is NOT grounds to reject it."
        ),
    }


def audit_split_game(parts: list[Path]) -> dict:
    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip
    )
    from tools.inspect_split_pkg import JoinedParts

    if not parts or len(parts) > 8:
        raise ValueError("Supply ordered private PS3 archive parts")
    with JoinedParts(parts) as stream:
        offset, length = unpack_stored_zip(stream)
        package = DebugPKG(stream, offset, length)
        matches = [entry for entry in package.items()
                   if entry["path"].lower() == "usrdir/cdata.psarc"]
        if len(matches) != 1:
            raise FormatError("Expected one private PSARC")
        arc = PSARC(package, matches[0]["offset"], matches[0]["size"])
        manifest = arc.manifest()
        models = [index + 1 for index, name in enumerate(manifest)
                  if name.lower().endswith(".bmodel")]
        clips = [index + 1 for index, name in enumerate(manifest)
                 if name.lower().endswith(".banim")]
        if len(models) > MAX_MODELS or len(clips) > MAX_ANIMATIONS:
            raise ValueError("Unexpected original resource count")

        def load_records(ids: list[int], limit: int):
            for index in ids:
                yield arc.entry_data(index, limit=limit)

        return audit_pose_records(
            load_records(models, MAX_MODEL_BYTES),
            load_records(clips, MAX_ANIM_BYTES),
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", type=Path, nargs="+",
                        help="Private PS3 debug-style package ZIP fragments")
    args = parser.parse_args(argv)
    try:
        result = audit_split_game(args.parts)
    except (ValueError, OSError) as error:
        print("Private local-pose audit did not validate", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
