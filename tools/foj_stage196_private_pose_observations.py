#!/usr/bin/env python3
"""Stage 196: OFFLINE operator-annotated PS3 / research-render comparison.

Compares 2D annotated correspondences after a per-frame 2D similarity
alignment, retaining rotation/translation/scale and reflected alternatives.
Does not read screenshots or video, contact an emulator, establish provenance,
prove the real actor/animation pairing, or attest the original PS3 engine.
All evidence and inputs are private. CI uses wholly invented landmarks.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
import re
import stat
import statistics
import sys
from typing import Any

SCHEMA = "foj.stage196.private_pose_landmarks.v1"
REPORT_SCHEMA = "foj.stage196.private_pose_alignment_report.v1"
MAX_BYTES = 131072
MAX_FRAMES = 12
MIN_FRAMES = 3
MIN_POINTS = 4
MAX_POINTS = 32
ID = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
TIMING_METHODS = frozenset({"manual_timestamp", "frame_clock_annotation"})


def rejected() -> ValueError:
    return ValueError("Private pose observation comparison rejected")


def pairs_unique(pairs):
    output = {}
    for key, val in pairs:
        if key in output:
            raise rejected()
        output[key] = val
    return output


def only_keys(obj: Any, expected: set[str]):
    if type(obj) is not dict or set(obj) != expected:
        raise rejected()


def real(value, low: float, high: float) -> float:
    if type(value) not in (float, int) or not math.isfinite(value):
        raise rejected()
    if not low <= value <= high:
        raise rejected()
    return float(value)


def capture_metadata(record: Any, expected_kind: str) -> tuple[float, bool]:
    only_keys(record, {"source_kind", "capture_recorded",
                       "timestamp_method", "timing_uncertainty_seconds"})
    if record["source_kind"] != expected_kind or (
            type(record["capture_recorded"]) is not bool):
        raise rejected()
    if record["timestamp_method"] not in TIMING_METHODS:
        raise rejected()
    uncertainty = real(record["timing_uncertainty_seconds"], 0., .08)
    return uncertainty, record["capture_recorded"]


def points_and_times(frame: Any):
    only_keys(frame, {"ps3_time_seconds", "experimental_time_seconds",
                       "landmarks"})
    a = real(frame["ps3_time_seconds"], 0., 600.)
    b = real(frame["experimental_time_seconds"], 0., 600.)
    marks = frame["landmarks"]
    if type(marks) is not list or not MIN_POINTS <= len(marks) <= MAX_POINTS:
        raise rejected()
    ids = set()
    reference, experimental = [], []
    for entry in marks:
        only_keys(entry, {"id", "ps3_xy", "experimental_xy"})
        name = entry["id"]
        if type(name) is not str or not ID.fullmatch(name) or name in ids:
            raise rejected()
        ids.add(name)
        for field, dest in (("ps3_xy", reference),
                            ("experimental_xy", experimental)):
            coord = entry[field]
            if type(coord) is not list or len(coord) != 2:
                raise rejected()
            dest.append((real(coord[0], 0., 1.),
                         real(coord[1], 0., 1.)))
    # Sorting by id prevents a change of input order from disguising a
    # wrong correspondence. Label strings are NEVER emitted in reports.
    order = sorted(range(len(marks)), key=lambda i: marks[i]["id"])
    return (a, b, tuple(sorted(ids)),
            [reference[i] for i in order],
            [experimental[i] for i in order])


def centered(points):
    n = len(points)
    cx = sum(p[0] for p in points) / n
    cy = sum(p[1] for p in points) / n
    offsets = [(x-cx, y-cy) for x,y in points]
    x2 = sum(x*x for x,y in offsets)
    y2 = sum(y*y for x,y in offsets)
    xy = sum(x*y for x,y in offsets)
    radius = math.sqrt((x2+y2)/n)
    # Disallow nearly collinear or identical landmarks: a visually
    # meaningless alignment can otherwise look like a perfect match.
    if radius < .015 or (x2*y2-xy*xy) / (x2+y2)**2 < .005:
        raise rejected()
    return (cx,cy), offsets, radius


def fit(reference, experimental, *, mirror=False):
    if len(reference)!=len(experimental) or len(reference)<MIN_POINTS:
        raise rejected()
    target_center, target, reference_radius = centered(reference)
    source = [(-x,y) if mirror else (x,y) for x,y in experimental]
    source_center, source_vectors, _source_radius = centered(source)
    dot = sum(x*u+y*v for (x,y),(u,v) in zip(source_vectors,target))
    cross = sum(x*v-y*u for (x,y),(u,v) in zip(source_vectors,target))
    denominator = sum(x*x+y*y for x,y in source_vectors)
    amplitude = math.hypot(dot, cross)
    if denominator < 1e-12 or amplitude < 1e-12:
        raise rejected()
    scale = amplitude/denominator
    if not .05 <= scale <= 20.:
        raise rejected()
    cost = 0.
    for (x,y),(u,v) in zip(source_vectors,target):
        px = (dot*x-cross*y)/denominator
        py = (cross*x+dot*y)/denominator
        cost += (px-u)**2 + (py-v)**2
    normalized_rms = math.sqrt(max(0., cost/len(reference)))/reference_radius
    if not math.isfinite(normalized_rms):
        raise rejected()
    # The implied translation and rotation are calculated internally,
    # never exported. They could identify the annotated original image.
    _ = (target_center, source_center)
    return normalized_rms


def shape_signature(points):
    _center, _, radius = centered(points)
    return tuple(
        math.dist(a,b)/radius for a,b in itertools.combinations(points,2)
    )


def temporal_signature_error(frames):
    signatures = [
        (shape_signature(ref),shape_signature(exp))
        for _ta,_tb,_ids,ref,exp in frames
    ]
    # Camera-translation / in-plane rotation / uniform-scale invariant:
    # compare relative changes in normalized inter-landmark distances.
    accum = count = 0
    for (ref0,exp0),(ref1,exp1) in zip(signatures,signatures[1:]):
        for a,b,c,d in zip(ref0,ref1,exp0,exp1):
            accum += ((b-a)-(d-c))**2
            count += 1
    return math.sqrt(accum/count) if count else 0.


def align_observations(observations: dict) -> dict:
    only_keys(observations, {"schema", "ps3_observation",
                             "experimental_observation", "frames"})
    if observations["schema"] != SCHEMA:
        raise rejected()
    ps3_uncertainty, ps3_declared = capture_metadata(
        observations["ps3_observation"], "original_ps3_playback")
    switch_uncertainty, switch_declared = capture_metadata(
        observations["experimental_observation"],
        "experimental_switch_research")
    frames = observations["frames"]
    if type(frames) is not list or not MIN_FRAMES <= len(frames) <= MAX_FRAMES:
        raise rejected()
    validated=[]
    last_a=last_b=-1.
    previous_ids = None
    differences=[]
    for frame in frames:
        row=points_and_times(frame)
        ta,tb,names,reference,experimental=row
        if ta<=last_a or tb<=last_b or (
            abs(ta-tb)>ps3_uncertainty+switch_uncertainty+.001):
            raise rejected()
        if previous_ids is not None and names != previous_ids:
            raise rejected()
        centered(reference)
        centered(experimental)
        validated.append(row)
        differences.append(abs(ta-tb))
        last_a,last_b=ta,tb
        previous_ids=names
    diagnostics=[]
    for _a,_b,_id,reference,experimental in validated:
        normal = fit(reference,experimental)
        reflected = fit(reference,experimental,mirror=True)
        diagnostics.append((normal,reflected))
    normal = [x for x,_ in diagnostics]
    mirrored = [x for _,x in diagnostics]
    temporal = temporal_signature_error(validated)
    return {
        "schema": REPORT_SCHEMA,
        "provenance": "operator-annotated-private-input-not-independently-verified",
        "number_of_frames": len(validated),
        "landmarks_per_frame": len(previous_ids),
        "max_declared_frame_time_delta_seconds": round(max(differences),6),
        "ordinary_similarity_normalized_rms_per_frame":
            [round(v,6) for v in normal],
        "reflected_similarity_normalized_rms_per_frame":
            [round(v,6) for v in mirrored],
        "ordinary_similarity_normalized_rms_median":
            round(statistics.median(normal),6),
        "reflected_similarity_normalized_rms_median":
            round(statistics.median(mirrored),6),
        "temporal_relative_shape_change_rms": round(temporal,6),
        "operator_declared_both_captures_recorded":
            ps3_declared and switch_declared,
        "original_ps3_capture_authenticity_verified": False,
        "experiment_capture_authenticity_verified": False,
        "original_model_animation_pair_verified": False,
        "ps3_bone_matrix_convention_verified": False,
        "switch_runtime_verified_by_this_tool": False,
        "automatic_handedness_selection": False,
        "source_images_or_landmarks_exported": False,
        "warning": (
            "Per-frame 2D similarity alignment removes camera translation, "
            "scale and in-plane rotation; it cannot resolve depth, occlusion, "
            "perspective, timing errors or genuine animation provenance. "
            "Reflected fit is diagnostic only, NOT proof of coordinate handedness."
        ),
    }


def blank_template():
    # There are deliberately no synthetic coordinates in the local
    # operator template: examples must never masquerade as real evidence.
    return {
        "schema": SCHEMA,
        "ps3_observation": {
            "source_kind": "original_ps3_playback",
            "capture_recorded": False,
            "timestamp_method": "manual_timestamp",
            "timing_uncertainty_seconds": .02,
        },
        "experimental_observation": {
            "source_kind": "experimental_switch_research",
            "capture_recorded": False,
            "timestamp_method": "manual_timestamp",
            "timing_uncertainty_seconds": .02,
        },
        "frames": [],
    }


def private_read(path: Path):
    try:
        st=path.lstat()
        if not stat.S_ISREG(st.st_mode) or not 1 <= st.st_size <= MAX_BYTES:
            raise rejected()
        raw=path.read_bytes()
        if len(raw)!=st.st_size:
            raise rejected()
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(rejected()),
        )
    except (OSError, UnicodeError, ValueError, RecursionError,
            json.JSONDecodeError):
        raise rejected() from None


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init",type=Path,
                      help="Create a new blank, unwitnessed local JSON template")
    mode.add_argument("--analyze",type=Path,
                      help="Analyze privately supplied observations offline")
    args=parser.parse_args(argv)
    try:
        if args.init is not None:
            with args.init.open("x", encoding="utf-8") as output:
                json.dump(blank_template(),output,indent=2)
                output.write("\n")
            print("Created BLANK local template. No observations claimed.")
        else:
            print(json.dumps(
                align_observations(private_read(args.analyze)),
                sort_keys=True,indent=2
            ))
        return 0
    except (OSError, ValueError, TypeError, OverflowError, ZeroDivisionError):
        # Reject without echoing user paths, annotation labels, raw landmark
        # positions or JSON fields from the private file.
        print("Private observation data rejected; inspect it offline.",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
