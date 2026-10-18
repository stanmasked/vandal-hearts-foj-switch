#!/usr/bin/env python3
"""Stage 208: operator-private leave-one-landmark-out camera nuisance audit.

Compare a 2D similarity (optionally reflected) to a full 2D affine fit.
Each evaluated landmark is excluded from both fits: a six-parameter
affine transformation cannot claim success merely by interpolating
the very point used to fit it. Affine benefit is a 2D hypothesis,
NEVER proof of original PS3 camera, perspective, bones or gameplay.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import sys

from tools.foj_stage196_private_pose_observations import (
    align_observations, centered, points_and_times, private_read, rejected
)

SCHEMA="foj.stage208.private_affine_crossvalidation.v1"
MIN_POINTS=5
MAX_DISTORTION=20.


def similarity_parameters(ref,exp,*,mirror=False):
    """Fit in-plane similarity, returns a prediction function and train RMS."""
    target_center,target,_=centered(ref)
    source=[(-x,y) if mirror else (x,y) for x,y in exp]
    source_center,vectors,_=centered(source)
    dot=sum(x*u+y*v for (x,y),(u,v) in zip(vectors,target))
    cross=sum(x*v-y*u for (x,y),(u,v) in zip(vectors,target))
    den=sum(x*x+y*y for x,y in vectors)
    if den<=1.e-12 or math.hypot(dot,cross)<=1.e-12:
        raise rejected()
    a,b=dot/den,cross/den
    scale=math.hypot(a,b)
    if not .05<=scale<=20.:
        raise rejected()

    def transform(point):
        x,y=point
        if mirror:
            x=-x
        x-=source_center[0]
        y-=source_center[1]
        return (target_center[0]+a*x-b*y,
                target_center[1]+b*x+a*y)

    square=sum(math.dist(transform(p),q)**2
               for p,q in zip(exp,ref))
    return transform,square/len(ref)


def affine_parameters(ref,exp):
    """Least-squares full 2D affine fit; reject singular or extreme maps."""
    (rx,ry),target,_=centered(ref)
    (ex,ey),source,_=centered(exp)
    xx=sum(x*x for x,y in source)
    xy=sum(x*y for x,y in source)
    yy=sum(y*y for x,y in source)
    det=xx*yy-xy*xy
    # A very thin configuration is unsafe, especially with leave-one-out.
    if det<=max(1.e-12,.001*(xx+yy)**2):
        raise rejected()
    ux=sum(x*u for (x,y),(u,v) in zip(source,target))
    uy=sum(y*u for (x,y),(u,v) in zip(source,target))
    vx=sum(x*v for (x,y),(u,v) in zip(source,target))
    vy=sum(y*v for (x,y),(u,v) in zip(source,target))
    a=(ux*yy-uy*xy)/det
    b=(uy*xx-ux*xy)/det
    c=(vx*yy-vy*xy)/det
    d=(vy*xx-vx*xy)/det
    frobenius=math.sqrt(a*a+b*b+c*c+d*d)
    determinant=a*d-b*c
    if (not math.isfinite(frobenius) or frobenius>40. or
        abs(determinant)<1.e-8):
        raise rejected()

    def transform(point):
        x=point[0]-ex
        y=point[1]-ey
        return (rx+a*x+b*y,ry+c*x+d*y)

    energy=a*a+b*b+c*c+d*d
    discriminant=math.sqrt(max(0.,energy*energy-4*determinant**2))
    largest=(energy+discriminant)/2.
    smallest=determinant**2/largest if largest>0 else 0.
    if smallest<=1.e-9:
        raise rejected()
    anisotropy=math.sqrt(largest/smallest)
    if not math.isfinite(anisotropy) or anisotropy>MAX_DISTORTION:
        raise rejected()
    return transform,anisotropy,1 if determinant>0 else -1


def compare(observations):
    base=align_observations(observations)
    frames=observations["frames"]
    normal_cv,affine_cv,stretch,affine_sign=[],[],[],[]
    unscorable=0
    for item in frames:
        _ta,_tb,_names,reference,experimental=points_and_times(item)
        n=len(reference)
        if n<MIN_POINTS:
            # With only four landmarks, leave-one-out affine has only
            # three training points and can interpolate rather than test.
            raise rejected()
        radius=centered(reference)[2]
        try:
            affine_full,ratio,sign=affine_parameters(reference,experimental)
            _=affine_full
            square_sim=square_affine=0.
            for heldout in range(n):
                refs=reference[:heldout]+reference[heldout+1:]
                exps=experimental[:heldout]+experimental[heldout+1:]
                options=[]
                for mirror in (False,True):
                    try:
                        transform,cost=similarity_parameters(
                            refs,exps,mirror=mirror
                        )
                    except ValueError:
                        # Only one reflected option may be singular or
                        # implausible on a badly annotated held-out fold.
                        continue
                    options.append((cost,transform))
                if not options:
                    raise rejected()
                # Pick a model using only the TRAINING landmarks.
                _cost,predictor=min(options,key=lambda item:item[0])
                aff,_,_=affine_parameters(refs,exps)
                square_sim+=math.dist(predictor(experimental[heldout]),
                                      reference[heldout])**2
                square_affine+=math.dist(aff(experimental[heldout]),
                                         reference[heldout])**2
            sim=math.sqrt(square_sim/n)/radius
            aff=math.sqrt(square_affine/n)/radius
        except ValueError:
            # Badly labelled or nearly singular geometry is an
            # UNRESOLVED frame. Never manufacture a low residual or
            # treat the remaining frames as proof of an affine camera.
            normal_cv.append(None)
            affine_cv.append(None)
            unscorable+=1
            continue
        normal_cv.append(sim)
        affine_cv.append(aff)
        stretch.append(ratio)
        affine_sign.append(sign)
    valid=[(s,a) for s,a in zip(normal_cv,affine_cv)
           if s is not None and a is not None]
    poor=sum(min(s,a)>.18 for s,a in valid)
    better=sum(
        s>=.05 and a+.012<.75*s and a<.18
        for s,a in valid
    )
    required=math.ceil(.6*len(frames))
    if not base["operator_declared_both_captures_recorded"]:
        status="operator_capture_not_declared"
    elif unscorable:
        status="unresolved_unscorable_geometry"
    elif poor:
        status="unresolved_projection_or_landmark_conflict"
    elif better>=required:
        status="tentative_affine_image_plane_nuisance"
    elif statistics.median(s for s,a in valid)<=.10 and better==0:
        status="two_d_similarity_sufficient"
    else:
        status="projection_model_ambiguous"
    def round_nullable(values,ndigits):
        return [round(x,ndigits) if x is not None else None
                for x in values]
    return {
        "schema":SCHEMA,
        "frames_evaluated":len(frames),
        "landmarks_per_frame":base["landmarks_per_frame"],
        "holdout_method":"leave_one_landmark_out_training_only",
        "similarity_holdout_rms_per_frame":round_nullable(normal_cv,6),
        "affine_holdout_rms_per_frame":round_nullable(affine_cv,6),
        "median_similarity_holdout_rms":(
            round(statistics.median(s for s,a in valid),6)
            if valid else None
        ),
        "median_affine_holdout_rms":(
            round(statistics.median(a for s,a in valid),6)
            if valid else None
        ),
        "median_affine_anisotropy_ratio":(
            round(statistics.median(stretch),4) if stretch else None
        ),
        "max_affine_anisotropy_ratio":(
            round(max(stretch),4) if stretch else None
        ),
        "affine_orientation_sign_consistent":(
            bool(affine_sign) and len(set(affine_sign))==1
            and not unscorable
        ),
        "affine_validation_improving_frames":better,
        "high_holdout_mismatch_frames":poor,
        "unscorable_geometry_frames":unscorable,
        "diagnosis":status,
        "both_capture_recordings_operator_declared":
            base["operator_declared_both_captures_recorded"],
        "original_ps3_camera_or_perspective_verified":False,
        "original_ps3_model_or_clip_verified":False,
        "original_ps3_pose_or_timing_verified":False,
        "source_capture_authenticated":False,
        "automatic_anatomical_landmark_authentication":False,
        "manual_labels_or_coordinates_exported":False,
        "warning":(
            "Cross-validated affine benefit can arise from perspective, "
            "camera, pose, mislabeled landmarks or other 2D distortion. "
            "Unscorable/ill-conditioned frames veto positive conclusions. "
            "This is not proof of original PS3 camera or skeletal math. "
            "Even small holdout errors do not verify original-game assets."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        record=compare(private_read(args.observations))
    except (ValueError,OSError,TypeError,ZeroDivisionError,OverflowError):
        print("Private Stage208 affine model audit rejected.",file=sys.stderr)
        return 2
    print(json.dumps(record,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
