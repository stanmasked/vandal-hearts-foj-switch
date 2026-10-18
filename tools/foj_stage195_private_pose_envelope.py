#!/usr/bin/env python3
"""Stage 195: purely LOCAL research diagnostics for owner-supplied FOJRM001
and one/two BANIM clips. Numeric displacement is in UNVERIFIED source units,
NOT proof of correct original PS3 poses or genuine clip-to-actor assignment.

No original vertices, bone arrays, file paths, names, hashes or animations
are printed or written; do not publish even the private aggregate report.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

from tools.check_local_rig_clip_set import inspect_clip_set, bounded_read
from tools.check_local_rig_pair import MAX_RIG_FILE, MAX_ANIM_FILE
from tools.decode_rig_banim import parse_banim, sample_local_pose
from tools.export_local_rigmesh import HEADER, BONE, SECTION, VERTEX, INFLUENCE
from tools.foj_stage195_pose_geometry import predict_vertices

SCHEMA="foj.stage195.private_pose_envelope.v1"
LABELS=("start","midpoint","end")
MAX_POSE_SAMPLES=6


def rig_geometry(data: bytes):
    """Private in-memory copy for bounded diagnostic only; caller validated."""
    magic, version, bones, vertex_count, section_count, flags = (
        HEADER.unpack_from(data,0)
    )
    if magic != b"FOJRM001" or version != 1 or flags or not bones:
        raise ValueError("Invalid research model format")
    pos=HEADER.size
    bind=[]
    for i in range(bones):
        parent,*values=BONE.unpack_from(data,pos)
        pos+=BONE.size
        if parent<-1 or parent>=i:
            raise ValueError("Invalid ordered skeleton")
        bind.append((parent,tuple(values[:4]),tuple(values[4:])))
    pos+=section_count*SECTION.size
    vertices=[]
    for _ in range(vertex_count):
        attrs=VERTEX.unpack_from(data,pos)
        pos+=VERTEX.size
        influence_count=attrs[-1]
        influences=[]
        for slot in range(5):
            idx,weight=INFLUENCE.unpack_from(data,pos)
            pos+=INFLUENCE.size
            if slot < influence_count:
                influences.append((idx,weight))
        vertices.append((tuple(attrs[:3]),tuple(influences)))
    if pos!=len(data):
        raise ValueError("Malformed private vertex buffer")
    return bind,vertices


def metrics(rest,positions):
    if len(rest)!=len(positions) or not positions:
        raise ValueError("Mismatched vertex positions")
    squared=0.
    furthest=0.
    for src,dest in zip(rest,positions,strict=True):
        distance_squared=sum((x-y)**2 for x,y in zip(src,dest,strict=True))
        if not math.isfinite(distance_squared):
            raise ValueError("Nonfinite private motion diagnostic")
        squared+=distance_squared
        furthest=max(furthest,math.sqrt(distance_squared))
    rms=math.sqrt(squared/len(positions))
    if not math.isfinite(rms):
        raise ValueError("Nonfinite private aggregate")
    return round(rms,5),round(furthest,5)


def inspect_pose_envelope(rig: bytes,primary: bytes,
                          secondary: bytes | None=None) -> dict:
    intake=inspect_clip_set(rig,primary,secondary)
    bind,vertices=rig_geometry(rig)
    if len(bind)!=intake["bone_count"] or len(vertices)!=intake["vertex_count"]:
        raise ValueError("Private model changed after intake")
    reference=predict_vertices(bind,bind,vertices)
    rest=[v[0] for v in vertices]
    bind_rms,bind_max=metrics(rest,reference)
    # The expected bind-world * inverse(bind-world) identity is a property
    # of the RESEARCH implementation. If violated, pose diagnostics unsafe.
    if bind_rms>0.001 or bind_max>0.001:
        raise ValueError("Research bind identity invariant failed")

    def report_clip(source: bytes):
        clip=parse_banim(source,retain_keys=True)
        values=[]
        for fraction,label in zip((0.,.5,1.),LABELS,strict=True):
            when=float(clip.duration)*fraction
            poses=sample_local_pose(clip,when)
            animated=[(b[0],p.rotation_xyzw,p.translation_xyz)
                      for b,p in zip(bind,poses,strict=True)]
            moved=predict_vertices(bind,animated,vertices)
            rms,maximum=metrics(rest,moved)
            values.append({
                "sample":label,
                "rms_source_vertex_displacement":rms,
                "max_source_vertex_displacement":maximum,
            })
        return values

    primary_metrics=report_clip(primary)
    secondary_metrics=report_clip(secondary) if secondary is not None else None
    if len(primary_metrics)+(len(secondary_metrics) if secondary_metrics else 0) > MAX_POSE_SAMPLES:
        raise ValueError("Private probe exceeded sample budget")
    return {
        "schema":SCHEMA,
        "scope":"private_source_coordinate_experiment_only",
        "bone_count":len(bind),
        "vertex_count":len(vertices),
        "root_count":intake["root_count"],
        "bind_identity_vertex_rms":bind_rms,
        "bind_identity_vertex_max":bind_max,
        "primary_pose_samples":primary_metrics,
        "secondary_pose_samples":secondary_metrics,
        "exact_hierarchy_compatible":True,
        "original_ps3_actor_clip_pairing_verified":False,
        "original_ps3_skinning_math_verified":False,
        "original_ps3_world_axis_convention_verified":False,
        "original_ps3_render_equivalence_verified":False,
        "physical_switch_runtime_verified":False,
        "warning":(
            "These displacements are in unknown source units under an "
            "experimental inverse-bind convention; small or large values "
            "must not be used to prove or reject genuine PS3 asset pairing."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rig",type=Path)
    parser.add_argument("primary",type=Path)
    parser.add_argument("--secondary",type=Path)
    args=parser.parse_args(argv)
    try:
        rig=bounded_read(args.rig,MAX_RIG_FILE)
        primary=bounded_read(args.primary,MAX_ANIM_FILE)
        secondary=(bounded_read(args.secondary,MAX_ANIM_FILE)
                   if args.secondary is not None else None)
        result=inspect_pose_envelope(rig,primary,secondary)
    except (OSError,ValueError,IndexError,OverflowError,ZeroDivisionError):
        # Do not leak private absolute paths or source data in diagnostics.
        print("Private pose envelope rejected; examine input locally.",
              file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
