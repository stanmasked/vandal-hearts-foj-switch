#!/usr/bin/env python3
"""Stage 209: private 2D articulated-motion coherence between adjacent frames.

Compares *changes* in normalized inter-landmark distances, not raw screen
positions or frame-by-frame camera fits. Reports suspicious intervals and
potential single-frame annotation swaps; does not authenticate original PS3
footage, camera, timebase, actor, or game animation fidelity.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys

from tools.foj_stage196_private_pose_observations import (
    align_observations, points_and_times, shape_signature, private_read,
    rejected
)

SCHEMA="foj.stage209.private_interframe_motion_coherence.v1"
ACTIVITY_FLOOR=.010
MISMATCH_ABSOLUTE=.025
MISMATCH_RELATIVE=.55
COSINE_LIMIT=.4
MAX_CLOCK_RATIO=1.25


def _rms(values):
    if not values:
        raise rejected()
    value=math.sqrt(sum(x*x for x in values)/len(values))
    if not math.isfinite(value):
        raise rejected()
    return value


def _intervals(observations):
    previous=None
    previous_time=None
    previous_exp_time=None
    for frame in observations["frames"]:
        ta,tb,names,source,experimental=points_and_times(frame)
        current=(shape_signature(source),shape_signature(experimental))
        if previous is not None:
            ref_delta=tuple(b-a for a,b in zip(previous[0],current[0]))
            exp_delta=tuple(b-a for a,b in zip(previous[1],current[1]))
            if len(ref_delta)!=len(exp_delta):
                raise rejected()
            src_activity=_rms(ref_delta)
            exp_activity=_rms(exp_delta)
            difference=_rms(tuple(a-b for a,b in zip(
                ref_delta,exp_delta
            )))
            if src_activity>1.e-9 and exp_activity>1.e-9:
                correlation=sum(a*b for a,b in zip(
                    ref_delta,exp_delta
                ))/(
                    len(ref_delta)*src_activity*exp_activity
                )
                correlation=max(-1.,min(1.,correlation))
            else:
                correlation=None
            source_dt=ta-previous_time
            exp_dt=tb-previous_exp_time
            if source_dt<=0. or exp_dt<=0.:
                raise rejected()
            yield {
                "source_activity":src_activity,
                "research_activity":exp_activity,
                "movement_disagreement":difference,
                "direction_correlation":correlation,
                "clock_interval_ratio":max(
                    source_dt/exp_dt,exp_dt/source_dt
                ),
            }
        previous=current
        previous_time=ta
        previous_exp_time=tb


def inspect(observations):
    validity=align_observations(observations)
    results=list(_intervals(observations))
    if len(results)!=len(observations["frames"])-1:
        raise rejected()
    informative=0
    mismatch_indices=[]
    time_mismatch=0
    one_side_static=0
    bad_direction=0
    for index,row in enumerate(results):
        src=row["source_activity"]
        exp=row["research_activity"]
        activity=max(src,exp)
        if activity>ACTIVITY_FLOOR:
            informative+=1
        if (src<ACTIVITY_FLOOR and exp>=.025) or (
            exp<ACTIVITY_FLOOR and src>=.025
        ):
            one_side_static+=1
        inconsistent=(
            activity>.015 and row["movement_disagreement"]>
            max(MISMATCH_ABSOLUTE,MISMATCH_RELATIVE*activity)
        )
        if row["direction_correlation"] is not None and (
            min(src,exp)>.015 and
            row["direction_correlation"]<COSINE_LIMIT
        ):
            bad_direction+=1
            inconsistent=True
        if inconsistent:
            mismatch_indices.append(index)
        if row["clock_interval_ratio"]>MAX_CLOCK_RATIO:
            time_mismatch+=1

    # One incorrect marked pose can spoil the two immediately
    # neighboring interframe displacement estimates. This only
    # *suggests* where a human should inspect original/research images.
    suspect_middle=sum(
        index-1 in mismatch_indices and index in mismatch_indices
        for index in range(1,len(observations["frames"])-1)
    )
    both_reported=validity["operator_declared_both_captures_recorded"]
    if not both_reported:
        diagnosis="operator_capture_not_declared"
    elif mismatch_indices:
        diagnosis="unresolved_local_motion_or_annotation_mismatch"
    elif time_mismatch:
        diagnosis="unresolved_interval_timebase_disagreement"
    elif informative<2:
        diagnosis="unresolved_insufficient_articulated_motion"
    else:
        diagnosis="shape_transition_consistent_only"
    return {
        "schema":SCHEMA,
        "frames_evaluated":len(observations["frames"]),
        "interframe_intervals":len(results),
        "landmarks_per_frame":validity["landmarks_per_frame"],
        "informative_motion_intervals":informative,
        "suspect_motion_intervals":len(mismatch_indices),
        "adjacent_suspect_interval_pairs":suspect_middle,
        "one_stream_static_other_moving_intervals":one_side_static,
        "opposing_motion_direction_intervals":bad_direction,
        "interval_clock_ratio_above_tolerance_count":time_mismatch,
        "largest_interframe_shape_difference_rms":
            round(max(x["movement_disagreement"] for x in results),6),
        "median_interframe_shape_difference_rms":
            round(statistics.median(
                x["movement_disagreement"] for x in results),6),
        "largest_relative_frame_interval_ratio":
            round(max(x["clock_interval_ratio"] for x in results),5),
        "diagnosis":diagnosis,
        "captures_recorded_operator_declared":both_reported,
        "source_capture_hardware_authenticated":False,
        "original_character_or_clip_authenticated":False,
        "gameplay_motion_fidelity_verified":False,
        "original_ps3_frame_clock_verified":False,
        "camera_perspective_recovered":False,
        "landmarks_anatomically_authenticated":False,
        "original_landmark_names_or_positions_published":False,
        "warning":(
            "Consecutive 2D shape-change consistency cannot distinguish "
            "incorrect annotations, genuine pose differences, occlusion, "
            "perspective or camera movements. Adjacent suspicious "
            "intervals indicate possible single-frame errors but never "
            "authenticate original PS3 gameplay or timing."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        result=inspect(private_read(args.observations))
        print(json.dumps(result,sort_keys=True,indent=2))
    except (OSError,ValueError,TypeError,OverflowError,ZeroDivisionError):
        print("Private Stage209 interframe coherence rejected.",file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
