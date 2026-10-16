#!/usr/bin/env python3
"""Validate a PRIVATE user-local FOJRM001 + BANIM pair (never export game bytes).

This is an independent compatibility checker for the eighth Nintendo Switch
research NRO. It reports format/parent/weight invariants and transform
differences; identical hierarchy does NOT prove original PS3 playback.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import struct
import sys

from tools.decode_rig_banim import parse_banim, sample_local_pose
from tools.export_local_rigmesh import (
    HEADER, BONE, SECTION, VERTEX, INFLUENCE, MAGIC,
    MAX_BONES, MAX_VERTICES, MAX_SECTIONS,
)

MAX_RIG_FILE = 2_000_000
MAX_ANIM_FILE = 8_000_000


def inspect_pair(rig_bytes: bytes, anim_bytes: bytes) -> dict:
    if not 28 <= len(rig_bytes) <= MAX_RIG_FILE:
        raise ValueError("Invalid FOJRM001 file length")
    header = HEADER.unpack_from(rig_bytes, 0)
    magic, version, bones, vertices, sections, flags = header
    if (magic != MAGIC or version != 1 or flags or not 1 <= bones <= MAX_BONES or
        not 3 <= vertices <= MAX_VERTICES or vertices % 3 or
        not 1 <= sections <= MAX_SECTIONS):
        raise ValueError("Invalid FOJRM001 header")
    expected = 28 + bones*BONE.size + sections*SECTION.size + vertices*(
        VERTEX.size + 5*INFLUENCE.size
    )
    if len(rig_bytes) != expected:
        raise ValueError("FOJRM001 length does not match header")
    pos = HEADER.size
    parents = []
    bind_q = []
    bind_xyz = []
    for i in range(bones):
        parent, *float_data = BONE.unpack_from(rig_bytes, pos)
        pos += BONE.size
        if parent < -1 or parent >= i:
            raise ValueError("Invalid model rig parent index")
        if not all(math.isfinite(v) for v in float_data):
            raise ValueError("Non-finite model bone transform")
        q = tuple(float_data[:4])
        if abs(sum(v*v for v in q)-1) > .04:
            raise ValueError("Model quaternion not normalized")
        parents.append(parent)
        bind_q.append(q)
        bind_xyz.append(tuple(float_data[4:]))

    covered = 0
    for i in range(sections):
        first, count = SECTION.unpack_from(rig_bytes, pos)
        pos += SECTION.size
        if first != covered or not count or count % 3 or covered+count > vertices:
            raise ValueError("Non-contiguous triangle section")
        covered += count
    if covered != vertices:
        raise ValueError("Incomplete geometry section coverage")

    weighted = 0
    total_influences = 0
    for i in range(vertices):
        data = VERTEX.unpack_from(rig_bytes, pos)
        pos += VERTEX.size
        count = data[-1]
        if count > 5 or not all(math.isfinite(v) for v in data[:-1]):
            raise ValueError("Invalid vertex attributes")
        weights = []
        for j in range(5):
            bone, w = INFLUENCE.unpack_from(rig_bytes, pos)
            pos += INFLUENCE.size
            if j < count:
                if bone >= bones or not math.isfinite(w) or w < 0 or w > 1.001:
                    raise ValueError("Out-of-range vertex influence")
                weights.append(w)
            elif bone != 0 or w != 0:
                raise ValueError("Non-zero unused influence")
        if count:
            if abs(sum(weights)-1) > .002:
                raise ValueError("Unnormalized vertex influences")
            weighted += 1
        total_influences += count
    if pos != len(rig_bytes):
        raise ValueError("Unexpected trailing rig mesh bytes")

    clip = parse_banim(anim_bytes, retain_keys=True)
    if len(clip.tracks) != bones or any(
        (-1 if track.parent is None else track.parent) != parents[i]
        for i, track in enumerate(clip.tracks)
    ):
        raise ValueError("BANIM track hierarchy does not match model rig")

    sample_times = (0.0, clip.duration/2, clip.duration)
    sample_reports = []
    for t in sample_times:
        local = sample_local_pose(clip, t)
        diffs = [
            math.sqrt(sum((a-b)**2 for a,b in
                          zip(local[i].translation_xyz, bind_xyz[i])))
            for i in range(bones)
        ]
        quat_dots = [
            abs(sum(a*b for a,b in zip(local[i].rotation_xyzw, bind_q[i])))
            for i in range(bones)
        ]
        sample_reports.append({
            "seconds": round(t, 6),
            "median_local_translation_difference": round(statistics.median(diffs), 6),
            "max_local_translation_difference": round(max(diffs), 6),
            "median_absolute_quaternion_dot": round(
                statistics.median(quat_dots), 6
            ),
        })
    return {
        "format": "FOJRM001",
        "section_count": sections,
        "vertex_count": vertices,
        "triangle_count": vertices//3,
        "bone_count": bones,
        "root_bone_count": parents.count(-1),
        "weighted_vertex_count": weighted,
        "influence_entries": total_influences,
        "animation_tracks": len(clip.tracks),
        "animation_keyframes": clip.key_count,
        "animation_duration_seconds": round(clip.duration, 6),
        "complete_parent_hierarchy_match": True,
        "local_pose_samples": sample_reports,
        "disclaimer": (
            "Matching hierarchy and finite sampled poses validate intake only; "
            "the original engine's bind/pose math and rendering are not verified."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rigmesh", type=Path, help="Local user-owned preview.fojrm")
    parser.add_argument("animation", type=Path, help="Local original preview.banim")
    args = parser.parse_args(argv)
    try:
        if (args.rigmesh.stat().st_size > MAX_RIG_FILE or
            args.animation.stat().st_size > MAX_ANIM_FILE):
            raise ValueError("Private input too large")
        result = inspect_pair(args.rigmesh.read_bytes(),
                              args.animation.read_bytes())
    except (OSError, ValueError) as exc:
        print(f"Private rig/BANIM verification error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
