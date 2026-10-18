#!/usr/bin/env python3
"""Stage211 owner-private multi-window source+research frame identity gate.

Requires 2–4 operator-provided observation sequences. Each gets a
different owner-local source PNG manifest and actual rendered research
PPM frame mapping. Checks images, not gameplay provenance. Never uploads,
outputs pixels, paths, SHA256, or manual coordinates.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from tools.foj_stage196_private_pose_observations import private_read,rejected,only_keys
from tools.foj_stage199_private_multiwindow import _read as read_windows,SCHEMA as WINDOWS_SCHEMA
from tools.foj_stage204_private_frame_landmarks import inspect_landmarks,read_bindings
from tools.foj_stage205_private_source_png import inspect_sources

SCHEMA="foj.stage211.private_multisequence_image_evidence.v1"
REPORT="foj.stage211.private_multisequence_image_audit.v1"
MAX_CONFIG_BYTES=32*1024


def read_configuration(path:Path):
    try:
        st=path.lstat()
        if not stat.S_ISREG(st.st_mode) or not 1<=st.st_size<=MAX_CONFIG_BYTES:
            raise rejected()
        # Strict duplicate JSON key checks from existing private_reader
        # are reused instead of logging secrets or filesystem paths.
        return private_read(path)
    except (OSError,ValueError,TypeError):
        raise rejected() from None


def verify(observations,config):
    only_keys(observations,{
        "schema","motion_independence_declaration","observations"
    })
    if observations["schema"]!=WINDOWS_SCHEMA:
        raise rejected()
    windows=observations["observations"]
    only_keys(config,{"schema","windows"})
    if (config["schema"]!=SCHEMA or type(windows) is not list or
        type(config["windows"]) is not list or
        not 2<=len(windows)<=4 or
        len(config["windows"])!=len(windows)):
        raise rejected()
    source_fingerprints=set()
    count=0
    same_frame=False
    validated_windows=[]
    # Validate all windows before any positive status, and never
    # authenticate capture independence from paths or separate hashes.
    for doc,binding in zip(windows,config["windows"],strict=True):
        only_keys(binding,{
            "source_png_dir","source_manifest",
            "research_frames_dir","research_binding"
        })
        if any(type(binding[key]) is not str or
               not 1<=len(binding[key])<=1024
               for key in binding):
            raise rejected()
        original=Path(binding["source_png_dir"])
        source_manifest=private_read(Path(binding["source_manifest"]))
        research=Path(binding["research_frames_dir"])
        research_manifest=read_bindings(Path(binding["research_binding"]))
        source=inspect_sources(doc,source_manifest,original)
        experimental=inspect_landmarks(doc,research_manifest,research)
        if source["source_png_frames_locally_bound"]!=experimental[
            "stage203_named_frames_bound"
        ]:
            raise rejected()
        frame_hashes=[f["sha256"] for f in source_manifest["frames"]]
        if any(h in source_fingerprints for h in frame_hashes):
            same_frame=True
        source_fingerprints.update(frame_hashes)
        count+=len(frame_hashes)
        validated_windows.append((
            doc,source_manifest,original,research_manifest,research
        ))
    # Re-read EVERY owner's source PNG and named research PPM after all
    # windows were examined. This detects files replaced during a
    # multiwindow run. Never cache a path-only "success" receipt.
    for doc,manifest,source_dir,frame_binding,research_dir in validated_windows:
        if inspect_sources(doc,manifest,source_dir)[
            "source_png_frames_locally_bound"
        ]!=inspect_landmarks(doc,frame_binding,research_dir)[
            "stage203_named_frames_bound"
        ]:
            raise rejected()
    # A cross-window replay of a byte-identical PNG is a hard failure
    # for independent evidence, even when file names and timestamps
    # differ. Genuine repeated static images can therefore be
    # conservatively marked unresolved.
    return {
        "schema":REPORT,
        "windows_verified":len(windows),
        "source_png_frames_checked":count,
        "research_ppm_frames_bound":count,
        "all_window_source_and_research_images_rechecked":True,
        "source_pngs_distinct_across_windows":not same_frame,
        "operator_declared_distinct_actions":(
            observations["motion_independence_declaration"]==
            "distinct_actions_operator_declared"
        ),
        "diagnosis":(
            "duplicate_source_png_between_windows" if same_frame else
            "source_and_research_images_locally_bound_only"
        ),
        "window_capture_independence_authenticated":False,
        "authentic_ps3_gameplay_verified":False,
        "correct_character_or_clip_verified":False,
        "original_animation_accuracy_verified":False,
        "source_png_bytes_or_hashes_exported":False,
        "research_ppm_pixels_exported":False,
        "private_directory_paths_exported":False,
        "warning":(
            "Content binding verifies private source PNG bytes and research "
            "wireframe annotation proximity only. Different PNG files do not "
            "prove independent PS3 recordings, source actors, true timestamps "
            "or original skeletal animation fidelity."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations",required=True,type=Path)
    parser.add_argument("--bindings",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        result=verify(read_windows(args.observations),
                      read_configuration(args.bindings))
    except (OSError,ValueError,TypeError,IndexError,OverflowError):
        print("Private Stage211 image binding rejected.",file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
