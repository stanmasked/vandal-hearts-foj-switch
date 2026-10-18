#!/usr/bin/env python3
"""Stage 199: offline multi-window consensus for privately annotated motion.

At most four bounded Stage 196 observations share a fixed candidate lag
grid. Each window's complete, unchanged interior timeline contributes
equal weight to training and held-out validation. The system can *only*
propose a tentative alignment; no original PS3 media or timing is verified.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import stat
import sys

from tools.foj_stage196_private_pose_observations import (
    blank_template, pairs_unique, points_and_times, private_read as _unused,
    rejected, shape_signature
)
from tools.foj_stage197_private_motion_lag import (
    _interpolate, _mean_square, _validate, compare
)
from tools.foj_stage198_motion_ambiguity import inspect as ambiguity_inspect

SCHEMA = "foj.stage199.private_multiwindow_consensus.v1"
REPORT_SCHEMA = "foj.stage199.private_multiwindow_report.v1"
MAX_BYTES = 512 * 1024
MIN_WINDOWS = 2
MAX_WINDOWS = 4
INDEPENDENCE = ("not_established", "distinct_actions_operator_declared")


def template():
    return {
        "schema": SCHEMA,
        "motion_independence_declaration": "not_established",
        "observations": [blank_template(), blank_template()],
    }


def _read(path: Path):
    try:
        info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= MAX_BYTES:
            raise rejected()
        raw=path.read_bytes()
        if len(raw)!=info.st_size:
            raise rejected()
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(rejected()),
        )
    except (OSError,ValueError,UnicodeError,RecursionError):
        raise rejected() from None


def _profile(document, *, max_shift, offsets):
    times,exp_times,_r,_e,indices,uncertainty,claimed=_validate(
        document,max_shift=max_shift
    )
    if len(indices)<5:
        raise rejected()
    rows=[points_and_times(frame) for frame in document["frames"]]
    reference=[shape_signature(item[3]) for item in rows]
    experimental=[shape_signature(item[4]) for item in rows]
    training,heldout=indices[::2],indices[1::2]
    if len(training)<3 or len(heldout)<2:
        raise rejected()

    def score(lag, selected):
        values=[]
        for idx in selected:
            guess=_interpolate(
                exp_times,experimental,times[idx]+lag
            )
            values.append(_mean_square(reference[idx],guess))
        return math.sqrt(sum(values)/len(values))
    return [(lag,score(lag,training),score(lag,heldout))
            for lag in offsets]


def evaluate(document, *, max_shift=.2, step=.025):
    if type(document) is not dict or set(document)!={
        "schema","motion_independence_declaration","observations"
    } or document["schema"]!=SCHEMA:
        raise rejected()
    independence=document["motion_independence_declaration"]
    if type(independence) is not str or independence not in INDEPENDENCE:
        raise rejected()
    observations=document["observations"]
    if type(observations) is not list or not MIN_WINDOWS<=len(observations)<=MAX_WINDOWS:
        raise rejected()
    # Strict parameters, bounds and grid checks are delegated to the
    # Stage 197 production analyzer.
    prior=[compare(doc,max_shift=max_shift,step=step)
           for doc in observations]
    analyses=[ambiguity_inspect(doc,max_shift=max_shift,step=step)
              for doc in observations]
    if any(a["original_stage197_verdict"] != p["diagnosis"]
           for a,p in zip(analyses,prior)):
        raise rejected()
    # Literal duplicate payloads cannot be advertised as separate windows.
    # Never echo their content/hashes into report or errors.
    fingerprints=[
        json.dumps(doc,sort_keys=True,separators=(",",":"),allow_nan=False)
        for doc in observations
    ]
    if len(set(fingerprints))!=len(fingerprints):
        raise rejected()
    n=round(max_shift/step)
    offsets=[round(j*float(step),8) for j in range(-n,n+1)]
    profiles=[
        _profile(doc,max_shift=max_shift,offsets=offsets)
        for doc in observations
    ]
    # Equal weight PER WINDOW, never preferentially count longer clips.
    aggregate=[]
    for i,lag in enumerate(offsets):
        train=math.sqrt(sum(curve[i][1]**2 for curve in profiles)/len(profiles))
        held=math.sqrt(sum(curve[i][2]**2 for curve in profiles)/len(profiles))
        aggregate.append((lag,train,held))
    choice=min(aggregate,key=lambda p:(p[1],abs(p[0]),p[0]))
    offset,train,held=choice
    zero=aggregate[n]
    separate=[p["best_candidate_offset_seconds"] for p in prior]
    consensus_tolerance=max(2*step,.05)
    disagreement=(
        max(separate)-min(separate)>consensus_tolerance+1e-8
    )
    distant=[
        p for p in aggregate
        if abs(p[0]-offset)>=max(3*step,.075)-1e-8
    ]
    alternatives=[
        p for p in distant
        if p[1]<=train+max(.006,.15*train)
        and p[2]<=held+max(.006,.15*held)
    ]
    edge=abs(offset)>=max_shift-.25*step
    leave_window_disagreements=0
    if len(profiles)>=2:
        for removed in range(len(profiles)):
            subset=[p for j,p in enumerate(profiles) if j!=removed]
            candidates=[
                (lag,math.sqrt(sum(x[i][1]**2 for x in subset)/len(subset)))
                for i,lag in enumerate(offsets)
            ]
            survivor=min(candidates,key=lambda p:(p[1],abs(p[0]),p[0]))
            if abs(survivor[0]-offset)>=consensus_tolerance-1e-8:
                leave_window_disagreements+=1

    local_ambiguities=sum(
        p["robustness_adjusted_verdict"] in (
            "ambiguous","ambiguous_motion_or_annotation",
            "unresolved_shape_disagreement"
        ) for p in analyses
    )
    marked=all(p["both_capture_recordings_operator_declared"] for p in prior)
    independently_declared=independence=="distinct_actions_operator_declared"
    holdout_improved=held+.002<zero[2]
    adequate=train<=.09 and held<=.10
    agreement=not disagreement and leave_window_disagreements==0
    clean=(independently_declared and marked and adequate and agreement
           and not alternatives and not edge and not local_ambiguities)
    if not adequate:
        status="unresolved_across_windows"
    elif disagreement:
        status="inconsistent_window_offsets"
    elif not clean:
        status="ambiguous_multiwindow"
    elif abs(offset)<=step:
        status="no_clear_common_shift"
    elif holdout_improved:
        status="tentative_common_shift"
    else:
        status="ambiguous_multiwindow"

    return {
        "schema": REPORT_SCHEMA,
        "source": "operator_annotated_private_only",
        "window_count":len(observations),
        "candidate_count":len(offsets),
        "offset_seconds":round(offset,6),
        "individual_window_offsets_seconds":[round(x,6) for x in separate],
        "joint_training_shape_rms":round(train,6),
        "joint_holdout_shape_rms":round(held,6),
        "zero_offset_joint_holdout_rms":round(zero[2],6),
        "distant_competitive_offsets_count":len(alternatives),
        "disagreeing_window_offsets":bool(disagreement),
        "leave_one_window_out_instability_count":leave_window_disagreements,
        "locally_ambiguous_window_count":local_ambiguities,
        "operator_declared_distinct_actions":independently_declared,
        "all_capture_recordings_operator_declared":marked,
        "search_edge_reached":bool(edge),
        "holdout_improved_over_zero":bool(holdout_improved),
        "diagnosis":status,
        "original_ps3_capture_authenticated":False,
        "source_actor_animation_binding_verified":False,
        "original_game_timing_verified":False,
        "nintendo_switch_execution_verified_by_tool":False,
        "original_landmarks_and_media_included":False,
        "warning":(
            "Even repeatable offsets do not authenticate source footage, "
            "prove motion-window independence, or recover original PS3 "
            "frame scheduling. A repeated cycle can alias every window."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init",type=Path)
    mode.add_argument("--analyze",type=Path)
    parser.add_argument("--max-shift",type=float,default=.2)
    parser.add_argument("--step",type=float,default=.025)
    args=parser.parse_args(argv)
    try:
        if args.init is not None:
            with args.init.open("x",encoding="utf-8") as output:
                json.dump(template(),output,indent=2)
                output.write("\n")
            print("Created BLANK private multi-window template; nothing authenticated.")
        else:
            result=evaluate(_read(args.analyze),
                            max_shift=args.max_shift,step=args.step)
            print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,TypeError,OverflowError,ZeroDivisionError):
        print("Private Stage 199 multi-window comparison rejected.",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
