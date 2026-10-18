#!/usr/bin/env python3
"""Stage 204: bind operator's research landmarks to ACTUAL Stage203 PPM frames.

This is an offline and *private* structural evidence gate. It requires that
each manually annotated experimental point lie on/near an actually rendered
wire segment in the explicitly named Stage203 production-C frame. It NEVER
claims authentication of original PS3 footage, source animation identity,
PS3 time, camera projection or original-game pose correctness.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import stat
import sys

from tools.foj_stage196_private_pose_observations import (
    align_observations, only_keys, private_read, rejected
)
from tools.foj_stage203_private_actor_evidence import (
    HEADER, IMAGE_BYTES, W, H
)

SCHEMA="foj.stage204.private_frame_binding.v1"
REPORT_SCHEMA="foj.stage204.private_wire_landmark_audit.v1"
STATE_ORDER=(
    "initial","play_025","paused","fade_0",
    "fade_025","fade_050","fade_075","fade_done","reset",
)
WIRE=b"\xda\xe4\xbd"
RADIUS=10  # bounded local wire-proximity tolerance, in PPM pixels


def read_bindings(path:Path):
    return private_read(path)


def validate_bindings(doc,observation_count):
    only_keys(doc,{"schema","frame_labels"})
    labels=doc["frame_labels"]
    if (doc["schema"]!=SCHEMA or type(labels) is not list or
        len(labels)!=observation_count or not 3<=len(labels)<=9):
        raise rejected()
    indices=[]
    for label in labels:
        if type(label) is not str or label not in STATE_ORDER:
            raise rejected()
        indices.append(STATE_ORDER.index(label))
    if indices!=sorted(set(indices)):
        raise rejected()
    return labels


def read_wire_frame(path:Path):
    st=path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_size!=IMAGE_BYTES:
        raise rejected()
    raw=path.read_bytes()
    if len(raw)!=IMAGE_BYTES or not raw.startswith(HEADER):
        raise rejected()
    pixels=raw[len(HEADER):]
    # Strict bounded true-color frame check. No images or pixels printed.
    if pixels.count(WIRE)<6:
        raise rejected()
    return pixels


def nearest_wire_distance(pixels,xy):
    x=int(round(xy[0]*(W-1)))
    y=int(round(xy[1]*(H-1)))
    best=(RADIUS+1)**2
    for iy in range(max(0,y-RADIUS),min(H,y+RADIUS+1)):
        row=iy*W*3
        for ix in range(max(0,x-RADIUS),min(W,x+RADIUS+1)):
            sq=(x-ix)**2+(y-iy)**2
            if sq>=best or sq>RADIUS**2:
                continue
            i=row+ix*3
            if pixels[i:i+3]==WIRE:
                best=sq
                if sq==0:
                    return 0.0
    if best>RADIUS**2:
        raise rejected()
    return math.sqrt(best)


def inspect_landmarks(observations, bindings, frames_dir:Path):
    # The shape validator ensures correspondence labels, monotonic clock,
    # bounded normalized points, no duplicate IDs, and noncollinear geometry.
    shape=align_observations(observations)
    rows=observations["frames"]
    names=validate_bindings(bindings,len(rows))
    st=frames_dir.lstat()
    if not stat.S_ISDIR(st.st_mode):
        raise rejected()
    distances=[]
    for row,label in zip(rows,names,strict=True):
        pixels=read_wire_frame(frames_dir/(label+".ppm"))
        d=[nearest_wire_distance(pixels,mark["experimental_xy"])
           for mark in row["landmarks"]]
        distances.append(round(max(d),3))
    return {
        "schema": REPORT_SCHEMA,
        "input_type": "operator_annotated_research_landmarks",
        "stage203_named_frames_bound":len(rows),
        "per_frame_max_research_wire_distance_pixels":distances,
        "research_landmarks_near_actual_native_ppm_wire":True,
        "original_ps3_capture_authenticated":False,
        "research_projection_or_camera_equivalence_verified":False,
        "original_actor_animation_binding_verified":False,
        "original_game_pose_accuracy_verified":False,
        "manual_anatomical_correspondences_verified":False,
        "stage203_research_frame_names_authenticated_only_locally":True,
        "operator_declared_both_captures_recorded":
            shape["operator_declared_both_captures_recorded"],
        "raw_frames_or_landmark_coordinates_exported":False,
        "warning":(
            "Wire proximity only confirms research-side annotation "
            "touches a chosen native image frame within 10 pixels. "
            "It does NOT authenticate original PS3 footage, verify "
            "manual landmark identities, infer exact pose timestamps, "
            "or establish matching original game animations."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",type=Path,required=True)
    parser.add_argument("--bindings",type=Path,required=True)
    parser.add_argument("--frames-dir",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=inspect_landmarks(
            private_read(args.observations),read_bindings(args.bindings),
            args.frames_dir
        )
    except (OSError,ValueError,TypeError,OverflowError,IndexError):
        print("Private Stage204 research-frame binding rejected.",
              file=sys.stderr)
        return 2
    # Even summary distances are private diagnostics: output solely to
    # owner's console in a manually invoked, offline process.
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
