#!/usr/bin/env python3
"""Stage207: owner-private per-frame 2D camera/pose/time consistency audit.

These are image-plane *hypotheses* fitted to operator landmarks; the
program cannot identify a real camera, 3D yaw/pitch, the right actor,
original PS3 frame timing or true source animation fidelity.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys

from tools.foj_stage196_private_pose_observations import (
    align_observations,centered,points_and_times,private_read,rejected
)
from tools.foj_stage197_private_motion_lag import compare as timing_compare

SCHEMA="foj.stage207.private_view_temporal_consistency.v1"
RAD=180./math.pi


def transform_fit(reference,experimental,*,mirror=False):
    """Fit experimental -> source by translation, uniform scale, rotation.

    Reuses Stage196's centered Procrustes model but retains only private
    aggregate scale/roll variation, never image centers or angle values.
    """
    if len(reference)!=len(experimental) or len(reference)<4:
        raise rejected()
    _t,target,ref_radius=centered(reference)
    source=[(-x,y) if mirror else (x,y) for x,y in experimental]
    _s,src,_r=centered(source)
    dot=sum(a*x+b*y for (a,b),(x,y) in zip(src,target))
    cross=sum(a*y-b*x for (a,b),(x,y) in zip(src,target))
    den=sum(a*a+b*b for a,b in src)
    amp=math.hypot(dot,cross)
    if den<=1e-12 or amp<=1e-12:
        raise rejected()
    scale=amp/den
    if not .05<=scale<=20.:
        raise rejected()
    angle=math.atan2(cross,dot)
    errors=0.
    for (a,b),(x,y) in zip(src,target):
        u=(dot*a-cross*b)/den
        v=(cross*a+dot*b)/den
        errors+=(u-x)**2+(v-y)**2
    rms=math.sqrt(max(0.,errors/len(ref)))/ref_radius if False else (
        math.sqrt(max(0.,errors/len(reference)))/ref_radius
    )
    if not math.isfinite(rms):
        raise rejected()
    return rms,scale,angle


def roll_span(angles):
    """Minimum angular arc containing all orientations; wrap-safe.

    Avoids interpreting -179 degrees -> +179 degrees as a 358-degree
    camera roll change.
    """
    if not angles:
        raise rejected()
    ordered=sorted((x%(2*math.pi)) for x in angles)
    gaps=[(ordered[(i+1)%len(ordered)]-ordered[i])%(2*math.pi)
          for i in range(len(ordered))]
    return (2*math.pi-max(gaps))*RAD


def inspect(observations):
    base=align_observations(observations)
    ordinary=[]
    reflected=[]
    for item in observations["frames"]:
        _a,_b,_names,ref,exp=points_and_times(item)
        ordinary.append(transform_fit(ref,exp))
        reflected.append(transform_fit(ref,exp,mirror=True))
    normal_rms=statistics.median(x[0] for x in ordinary)
    refl_rms=statistics.median(x[0] for x in reflected)
    best_mirror=refl_rms<normal_rms
    best=reflected if best_mirror else ordinary
    gap=abs(normal_rms-refl_rms)
    orientation_ambiguous=gap<=.025
    # A per-frame change of best reflection is a marker of mismatched
    # silhouettes/annotation, never automatic 3D handedness evidence.
    strongly_disagreeing=0
    for normal,mirror in zip(ordinary,reflected):
        preferred=mirror[0]+.025<normal[0]
        opposite=normal[0]+.025<mirror[0]
        if (best_mirror and opposite) or (not best_mirror and preferred):
            strongly_disagreeing+=1
    span=roll_span([item[2] for item in best])
    scales=[item[1] for item in best]
    size_ratio=max(scales)/min(scales)
    max_error=max(item[0] for item in best)
    fit_median=statistics.median(item[0] for item in best)
    unstable=(span>15. or size_ratio>1.30 or
              strongly_disagreeing>0 or max_error>.18 or
              fit_median>.09)

    if len(observations["frames"])>=8:
        try:
            timing=timing_compare(observations)
            time_status=timing["diagnosis"]
            offset=timing["best_candidate_offset_seconds"]
        except (ValueError,OverflowError,ZeroDivisionError):
            time_status="not_resolvable_from_motion"
            offset=None
    else:
        time_status="insufficient_frames_for_lag_estimation"
        offset=None

    reported=base["operator_declared_both_captures_recorded"]
    if not reported:
        assessment="operator_capture_not_declared"
    elif orientation_ambiguous:
        assessment="image_plane_orientation_ambiguous"
    elif unstable:
        assessment="possible_view_or_pose_inconsistency"
    elif time_status=="tentative_nonzero_shift":
        assessment="timing_offset_requires_manual_review"
    else:
        assessment="image_plane_similarity_stable_only"

    return {
        "schema":SCHEMA,
        "frames_evaluated":len(best),
        "landmarks_per_frame":base["landmarks_per_frame"],
        "mirror_model_preference":
            ("reflected" if best_mirror else "unreflected"),
        "mirror_preference_ambiguous":orientation_ambiguous,
        "relative_median_fit_advantage":round(gap,6),
        "per_frame_disagreement_with_global_orientation":
            strongly_disagreeing,
        "max_image_plane_orientation_change_degrees":round(span,3),
        "relative_apparent_size_span_ratio":round(size_ratio,4),
        "selected_similarity_rms_median":round(fit_median,6),
        "selected_similarity_rms_worst":round(max_error,6),
        "temporal_diagnostic":time_status,
        "temporal_candidate_offset_seconds":offset,
        "diagnosis":assessment,
        "both_capture_recordings_operator_declared":reported,
        "camera_yaw_pitch_or_3d_projection_verified":False,
        "source_ps3_capture_authenticated":False,
        "ps3_character_or_clip_identity_verified":False,
        "camera_motion_independently_measured":False,
        "original_animation_timing_verified":False,
        "gameplay_animation_fidelity_verified":False,
        "source_or_research_image_pixels_included":False,
        "landmark_coordinates_included":False,
        "warning":(
            "2D similarity rotation and size may reflect animation, "
            "pose, perspective or camera motion; no cause is isolated. "
            "A reflected fit cannot prove 3D handedness. Lag estimates "
            "are operator annotation hypotheses, never PS3 game timing."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=inspect(private_read(args.observations))
        print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except (ValueError,OSError,TypeError,OverflowError,ZeroDivisionError):
        print("Private Stage207 view/time analysis rejected.",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
