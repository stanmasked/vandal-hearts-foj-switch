#!/usr/bin/env python3
"""Stage210: private multi-sequence motion-coherence consensus.

Aggregates two to four Stage209 observational checks and guards against
replaying the same normalized motion under different coordinate order,
scale, translation, rotation, reflection or timestamps. A manifest's
independence declaration is NOT authenticated original-game evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from tools.foj_stage196_private_pose_observations import (
    points_and_times,shape_signature,rejected
)
from tools.foj_stage199_private_multiwindow import (
    SCHEMA as INPUT_SCHEMA,MIN_WINDOWS,MAX_WINDOWS,INDEPENDENCE,_read
)
from tools.foj_stage209_private_motion_coherence import inspect

SCHEMA="foj.stage210.private_multisequence_motion_consistency.v1"
COHERENT="shape_transition_consistent_only"


def normalized_sequence_fingerprint(document):
    # Exclude metadata clocks and operator-controlled ordering:
    # a geometrically identical replay must not count as a new action.
    signatures=[]
    for frame in document["frames"]:
        _ta,_tb,identifiers,source,experimental=points_and_times(frame)
        signatures.append([
            [round(x,6) for x in shape_signature(source)],
            [round(x,6) for x in shape_signature(experimental)],
        ])
    encoding=json.dumps(signatures,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(encoding.encode("ascii")).digest()


def evaluate(document):
    if (type(document) is not dict or
        set(document)!={"schema","motion_independence_declaration",
                        "observations"} or
        document["schema"]!=INPUT_SCHEMA):
        raise rejected()
    independence=document["motion_independence_declaration"]
    if type(independence) is not str or independence not in INDEPENDENCE:
        raise rejected()
    samples=document["observations"]
    if type(samples) is not list or not MIN_WINDOWS<=len(samples)<=MAX_WINDOWS:
        raise rejected()
    audits=[inspect(item) for item in samples]
    fingerprints=[normalized_sequence_fingerprint(doc) for doc in samples]
    # Duplicate *shape trajectories* cannot be counted as independent
    # even if camera orientation, order or filenames are changed.
    unique=len(set(fingerprints))==len(fingerprints)
    coherent=sum(x["diagnosis"]==COHERENT for x in audits)
    informative=sum(x["informative_motion_intervals"]>=2 for x in audits)
    uncertain=sum(x["diagnosis"]!=COHERENT for x in audits)
    suspect=sum(x["suspect_motion_intervals"] for x in audits)
    clock=sum(x["interval_clock_ratio_above_tolerance_count"] for x in audits)
    all_recorded=all(x["captures_recorded_operator_declared"] for x in audits)
    declared=independence=="distinct_actions_operator_declared"
    if not unique:
        status="duplicate_normalized_trajectory_not_independent"
    elif not all_recorded:
        status="one_or_more_captures_not_declared"
    elif not declared:
        status="window_independence_not_established"
    elif any(x["diagnosis"]=="unresolved_local_motion_or_annotation_mismatch"
             for x in audits):
        status="unresolved_motion_difference_between_windows"
    elif any(x["diagnosis"]=="unresolved_interval_timebase_disagreement"
             for x in audits):
        status="unresolved_window_timebase_disagreement"
    elif informative<len(samples):
        status="unresolved_insufficient_motion_windows"
    elif uncertain:
        status="unresolved_inconsistent_window_diagnoses"
    else:
        status="tentative_operator_declared_multisequence_coherence_only"
    return {
        "schema":SCHEMA,
        "windows_evaluated":len(samples),
        "distinct_normalized_trajectories_detected":len(set(fingerprints)),
        "duplicate_normalized_motion_detected":not unique,
        "operator_declared_distinct_actions":declared,
        "all_source_and_research_captures_operator_declared":all_recorded,
        "coherent_2d_sequence_windows":coherent,
        "windows_with_informative_motion":informative,
        "unresolved_sequence_windows":uncertain,
        "total_suspicious_motion_intervals":suspect,
        "total_declared_clock_ratio_warnings":clock,
        "per_window_diagnoses":[x["diagnosis"] for x in audits],
        "diagnosis":status,
        "motion_window_independence_authenticated":False,
        "original_ps3_video_provenance_verified":False,
        "original_ps3_actor_or_clip_binding_verified":False,
        "original_ps3_animation_fidelity_verified":False,
        "actual_ps3_motion_timebase_verified":False,
        "private_landmarks_and_source_hashes_exported":False,
        "warning":(
            "Even different normalized 2D trajectories and matching motion "
            "cannot prove independent source captures, original PS3 gameplay, "
            "camera/occlusion agreement or actual animation correctness. "
            "Identical normalized trajectories can occur in legitimate "
            "repetitions and are conservatively not counted as independent."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        record=evaluate(_read(args.analyze))
    except (OSError,ValueError,TypeError,OverflowError,ZeroDivisionError):
        print("Private Stage210 multi-sequence audit rejected.",
              file=sys.stderr)
        return 2
    print(json.dumps(record,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
