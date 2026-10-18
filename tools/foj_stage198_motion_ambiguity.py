#!/usr/bin/env python3
"""Stage 198: private-only sensitivity checks for Stage 197 timing results.

Test whether an apparent lag survives removing one landmark, whether a
single bad frame dominates the score, and whether distant candidate shifts
are plausible on independent holdout frames. This cannot authenticate
source PS3 footage or identify its true animation timing.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys

from tools.foj_stage196_private_pose_observations import (
    points_and_times, private_read, shape_signature, rejected
)
from tools.foj_stage197_private_motion_lag import (
    _validate, _mean_square, _interpolate, compare
)

SCHEMA = "foj.stage198.private_motion_ambiguity.v1"
MAX_REMOVALS = 32


def profile(ref_times, experimental_times, reference, experimental, indices,
            offsets, *, excluded=None):
    if excluded is not None and not 0 <= excluded < len(reference[0]):
        raise rejected()
    ref_signatures = [
        shape_signature([p for j,p in enumerate(frame) if j != excluded])
        for frame in reference
    ]
    exp_signatures = [
        shape_signature([p for j,p in enumerate(frame) if j != excluded])
        for frame in experimental
    ]
    training, holdout = indices[::2], indices[1::2]
    if len(training)<3 or len(holdout)<2:
        raise rejected()
    result = []
    for offset in offsets:
        frame_errors = []
        for idx in indices:
            trial = _interpolate(
                experimental_times, exp_signatures, ref_times[idx]+offset
            )
            frame_errors.append(math.sqrt(
                _mean_square(ref_signatures[idx], trial)
            ))
        train = math.sqrt(sum(frame_errors[j]**2 for j in range(
            0,len(frame_errors),2))/len(training))
        held = math.sqrt(sum(frame_errors[j]**2 for j in range(
            1,len(frame_errors),2))/len(holdout))
        result.append((offset, train, held, frame_errors))
    return result


def inspect(document, *, max_shift=.2, step=.025):
    # Stage 197 guards, captured declarations, and its original verdict
    # remain authoritative. This stage can only downgrade the verdict.
    previous = compare(document, max_shift=max_shift, step=step)
    ts,es,_sr,_se,indices,uncertainty,claimed = _validate(
        document,max_shift=max_shift
    )
    observations = [points_and_times(frame)
                    for frame in document["frames"]]
    landmarks = len(observations[0][2])
    if landmarks > MAX_REMOVALS:
        raise rejected()
    reference = [row[3] for row in observations]
    experimental = [row[4] for row in observations]
    count = round(max_shift/step)
    offsets = [round(i*step,8) for i in range(-count,count+1)]
    results = profile(ts,es,reference,experimental,indices,offsets)
    best = min(results,key=lambda p:(p[1],abs(p[0]),p[0]))
    lag,training,heldout,frame_residuals = best
    if abs(lag-previous["best_candidate_offset_seconds"])>1e-6:
        raise rejected()  # independent recomputation must agree

    median = statistics.median(frame_residuals)
    worst = max(frame_residuals)
    outlier_threshold=max(.03,3*median+.012)
    bad_frames=sum(x>outlier_threshold for x in frame_residuals)
    # The rejected-frame count is not proof that the *annotation*, rather
    # than camera or actual motion, is wrong.
    distant = [
        p for p in results
        if abs(p[0]-lag)>=max(3*step,.075)-1e-8
    ]
    plausible = [
        p for p in distant
        if p[1] <= training+max(.006,.15*training)
        and p[2] <= heldout+max(.006,.15*heldout)
    ]
    period_alias = bool(plausible)

    if landmarks<5:
        # Dropping a marker from four produces a degenerate 3-point
        # profile. Existing Stage 197 cannot certify redundancy here.
        drop_count = 0
        shifted = 0
        jackknife_deltas = []
    else:
        drop_count = landmarks
        shifted = 0
        jackknife_deltas = []
        for removed in range(landmarks):
            try:
                trial = profile(
                    ts,es,reference,experimental,indices,offsets,
                    excluded=removed
                )
            except ValueError:
                # Losing a key point destroyed geometric observability.
                shifted += 1
                continue
            chosen=min(trial,key=lambda p:(p[1],abs(p[0]),p[0]))
            difference=abs(chosen[0]-lag)
            jackknife_deltas.append(difference)
            if difference>=max(2*step,.05)-1e-8:
                shifted+=1

    ambiguity = (
        period_alias or bad_frames>0 or shifted>0 or landmarks<5
    )
    verdict=previous["diagnosis"]
    if ambiguity and verdict in ("tentative_nonzero_shift","no_clear_shift"):
        verdict="ambiguous_motion_or_annotation"
    return {
        "schema": SCHEMA,
        "source_diagnostic_schema": previous["schema"],
        "original_stage197_verdict": previous["diagnosis"],
        "robustness_adjusted_verdict": verdict,
        "estimated_offset_seconds": previous["best_candidate_offset_seconds"],
        "candidate_search_size": len(offsets),
        "fixed_interior_frames": len(indices),
        "landmarks_count": landmarks,
        "jackknife_landmarks_checked": drop_count,
        "jackknife_lag_changes_count": shifted,
        "largest_jackknife_shift_seconds": (
            round(max(jackknife_deltas),6) if jackknife_deltas else None
        ),
        "suspicious_frame_count": bad_frames,
        "largest_frame_shape_residual": round(worst,6),
        "median_frame_shape_residual": round(median,6),
        "distinct_plausible_shift_count": len(plausible),
        "possible_repeating_motion_alias": period_alias,
        "possible_annotation_or_camera_disagreement": bad_frames>0,
        "landmark_sensitivity_unstable": shifted>0,
        "sufficient_landmark_redundancy": landmarks>=5,
        "both_capture_recordings_operator_declared": claimed,
        "original_ps3_capture_authenticated": False,
        "experimental_capture_authenticated": False,
        "original_game_timing_verified": False,
        "original_engine_matrix_convention_verified": False,
        "raw_source_landmarks_included": False,
        "interpretation": (
            "Sensitivity tests only: outliers may reflect actual poses, "
            "camera mismatch or manual annotation errors. Near-equivalent "
            "lag candidates may reflect repeating motion or sampling alias. "
            "Nothing here authenticates original PS3 gameplay footage."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze",type=Path,required=True)
    parser.add_argument("--max-shift",type=float,default=.2)
    parser.add_argument("--step",type=float,default=.025)
    args=parser.parse_args(argv)
    try:
        result=inspect(
            private_read(args.analyze),
            max_shift=args.max_shift,step=args.step
        )
        print(json.dumps(result,sort_keys=True,indent=2))
    except (OSError,ValueError,TypeError,OverflowError,ZeroDivisionError):
        print("Private Stage 198 motion diagnostic rejected.",file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
