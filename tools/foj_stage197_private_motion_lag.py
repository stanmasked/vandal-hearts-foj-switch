#!/usr/bin/env python3
"""Stage 197: OFFLINE exploratory lag diagnostic for private pose landmarks.

Estimate constant time offset from moving, 2D similarity-invariant
inter-landmark distances. Compare a fixed interior time window across all
candidate shifts with odd/even hold-out checks. No screenshot reading,
no source authenticity verification, no verified PS3 scheduler/rig math.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys

from tools.foj_stage196_private_pose_observations import (
    SCHEMA as INPUT_SCHEMA, TIMING_METHODS, capture_metadata,
    only_keys, points_and_times, private_read, shape_signature, rejected,
)

SCHEMA = "foj.stage197.private_motion_timing_lag.v1"
MIN_FRAMES = 8
MAX_FRAMES = 12
MIN_INTERIOR = 5
MAX_GRID_POINTS = 61


def _mean_square(a, b):
    if len(a) != len(b) or not a:
        raise rejected()
    squared = sum((x-y)*(x-y) for x,y in zip(a,b))
    if not math.isfinite(squared):
        raise rejected()
    return squared / len(a)


def _variation(signatures):
    if not signatures:
        raise rejected()
    n = len(signatures[0])
    if not n or any(len(s) != n for s in signatures):
        raise rejected()
    mean = [sum(sig[i] for sig in signatures)/len(signatures)
            for i in range(n)]
    return math.sqrt(sum(_mean_square(sig, mean)
                         for sig in signatures)/len(signatures))


def _interpolate(times, values, when):
    if when < times[0]-1e-7 or when > times[-1]+1e-7:
        raise rejected()
    if when <= times[0]:
        return values[0]
    for i in range(1,len(times)):
        if when <= times[i]+1e-7:
            dt=times[i]-times[i-1]
            if dt<=0:
                raise rejected()
            w=max(0.,min(1.,(when-times[i-1])/dt))
            return tuple(
                (1-w)*a+w*b for a,b in zip(values[i-1],values[i])
            )
    return values[-1]


def _validate(document, *, max_shift):
    only_keys(document, {"schema", "ps3_observation",
                         "experimental_observation", "frames"})
    if document["schema"] != INPUT_SCHEMA:
        raise rejected()
    ps3_precision, ps3_reported = capture_metadata(
        document["ps3_observation"], "original_ps3_playback")
    exp_precision, exp_reported = capture_metadata(
        document["experimental_observation"],
        "experimental_switch_research")
    rows=document["frames"]
    if type(rows) is not list or not MIN_FRAMES<=len(rows)<=MAX_FRAMES:
        raise rejected()
    ref_times,exp_times,refs,exps=[],[],[],[]
    names=None
    for row in rows:
        ta,tb,ids,reference,experimental=points_and_times(row)
        if names is not None and ids!=names:
            raise rejected()
        names=ids
        if (ref_times and ta<=ref_times[-1]) or (
                exp_times and tb<=exp_times[-1]):
            raise rejected()
        ref_times.append(ta)
        exp_times.append(tb)
        refs.append(shape_signature(reference))
        exps.append(shape_signature(experimental))

    if _variation(refs)<.012 or _variation(exps)<.012:
        # Without pose changes, minimizing residual cannot establish lag.
        raise rejected()
    if any(b-a>1.0 for a,b in zip(ref_times,ref_times[1:])) or (
            any(b-a>1.0 for a,b in zip(exp_times,exp_times[1:]))):
        raise rejected()
    interior = [i for i,t in enumerate(ref_times)
                if exp_times[0]+max_shift-1e-7<=t<=exp_times[-1]-max_shift+1e-7]
    if len(interior)<MIN_INTERIOR:
        # Every candidate must use the SAME subset of original frames.
        raise rejected()
    return (ref_times,exp_times,refs,exps,interior,
            ps3_precision+exp_precision,ps3_reported and exp_reported)


def compare(document, *, max_shift=.2, step=.025):
    if (type(max_shift) not in (float,int) or
        type(step) not in (float,int) or
        not math.isfinite(max_shift) or not math.isfinite(step) or
        not .025<=max_shift<=.3 or not .005<=step<=.1):
        raise rejected()
    count=round(max_shift/step)
    if (abs(max_shift/step-count)>1e-7 or
            count<2 or count*2+1>MAX_GRID_POINTS):
        raise rejected()
    offsets=[round(j*float(step),8) for j in range(-count,count+1)]
    ref_t,exp_t,refs,exps,indices,uncertainty,claimed = _validate(
        document,max_shift=float(max_shift))
    # Fixed, predeclared split: fit offsets on one set and check the other.
    training=indices[::2]
    holdout=indices[1::2]
    if len(training)<3 or len(holdout)<2:
        raise rejected()

    def score(lag, selected):
        residual=[]
        for i in selected:
            trial=_interpolate(exp_t,exps,ref_t[i]+lag)
            residual.append(_mean_square(refs[i],trial))
        return math.sqrt(sum(residual)/len(residual))

    scores=[(shift,score(shift,training),score(shift,holdout))
            for shift in offsets]
    winner=min(scores,key=lambda row:(row[1],abs(row[0]),row[0]))
    baseline=next(s for s in scores if s[0]==0.)
    shift,train,validation=winner
    competing=[row for row in scores
               if abs(row[0]-shift)>=max(3*step,.05)]
    alternative=min(competing,key=lambda row:row[1]) if competing else None
    ambiguous = (alternative is not None and
                 alternative[1] <= train+.006)
    at_edge=abs(shift)>=max_shift-step*.25
    heldout_improves=validation+.002 < baseline[2]
    good_fit=train<=.09 and validation<=.10
    time_precision_ok=uncertainty<=max(2*step,.025)
    if not good_fit:
        status="unresolved_shape_disagreement"
    elif ambiguous or at_edge or not time_precision_ok:
        status="ambiguous"
    elif abs(shift)<=step:
        status="no_clear_shift"
    elif heldout_improves:
        status="tentative_nonzero_shift"
    else:
        status="ambiguous"

    return {
        "schema":SCHEMA,
        "evidence_level":"operator_annotated_only_no_media_authentication",
        "samples_total":len(ref_t),
        "common_interior_samples":len(indices),
        "training_samples":len(training),
        "heldout_samples":len(holdout),
        "scan_max_abs_seconds":round(max_shift,6),
        "scan_step_seconds":round(step,6),
        "best_candidate_offset_seconds":round(shift,6),
        "offset_definition": (
            "Match original(t) to experimental(t + offset). "
            "A positive offset indicates later annotated experimental motion."
        ),
        "best_train_shape_rms":round(train,6),
        "best_holdout_shape_rms":round(validation,6),
        "zero_offset_train_shape_rms":round(baseline[1],6),
        "zero_offset_holdout_shape_rms":round(baseline[2],6),
        "distant_alternative_train_shape_rms":
            round(alternative[1],6) if alternative else None,
        "diagnosis":status,
        "search_edge_reached":bool(at_edge),
        "distant_alternative_competitive":bool(ambiguous),
        "declared_uncertainty_allows_step_resolution":bool(time_precision_ok),
        "holdout_improved_over_zero_offset":bool(heldout_improves),
        "both_capture_recordings_operator_declared":bool(claimed),
        "original_ps3_capture_authenticated":False,
        "experimental_capture_authenticated":False,
        "original_animation_pacing_verified":False,
        "original_bone_convention_verified":False,
        "nintendo_switch_execution_verified_by_tool":False,
        "raw_landmarks_and_source_images_in_report":False,
        "warning": (
            "Diagnostic lag is NOT a verified PS3-versus-Switch clock offset. "
            "Interpolated 2D distances lose reflection, translation, camera "
            "rotation, scale and depth. Periodicity, occlusion, wrong "
            "landmark identity or camera perspective may mimic a shift."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze",type=Path,required=True)
    parser.add_argument("--max-shift",type=float,default=.2)
    parser.add_argument("--step",type=float,default=.025)
    args=parser.parse_args(argv)
    try:
        result=compare(private_read(args.analyze),
                       max_shift=args.max_shift,step=args.step)
        print(json.dumps(result,indent=2,sort_keys=True))
    except (OSError,ValueError,TypeError,OverflowError,ZeroDivisionError):
        print("Private motion-timing observation rejected; inspect offline.",
              file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
