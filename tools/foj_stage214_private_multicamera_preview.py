#!/usr/bin/env python3
"""Stage214: owner-private multi-camera production-C rigged-actor previews.

Renders 2-9 camera settings against the exact same local rig/BANIM
inputs, compiling the real production C rigged-actor renderer just
once. Each view produces the nine real C frames and a contact-sheet
tile. No original-game file, screenshot, path, hash, or camera setting
is ever sent to GitHub or written to stdout.

This does not detect original PS3 camera parameters, bone accuracy,
character identity, or animation fidelity.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys

from tools.check_local_rig_clip_set import bounded_read
from tools.check_local_rig_pair import MAX_RIG_FILE,MAX_ANIM_FILE
from tools.foj_stage195_private_pose_envelope import inspect_pose_envelope
from tools.foj_stage200_prepare_private_sd import prepare
from tools.foj_stage203_private_actor_evidence import (
    HEADER,IMAGE_BYTES,W,H,STATES,
    compile_host,protected_json,render_evidence,run_native,
    safe_destination,validated_camera
)

SCHEMA="foj.stage214.private_multicamera_comparison.v1"
MIN_VIEWS,MAX_VIEWS=2,9
PREVIEW_FRAME="play_025"
MAX_SHEET_BYTES=3*W*3*H*3


def parse_view(value):
    if type(value) is not str:
        raise ValueError("Invalid research camera")
    entries=value.split(",")
    if len(entries)!=3:
        raise ValueError("Research camera must have three numbers")
    try:
        candidates=tuple(float(x) for x in entries)
    except (ValueError,OverflowError):
        raise ValueError("Invalid research camera") from None
    return validated_camera(*candidates)


def validate_views(views):
    if (type(views) not in (tuple,list) or
        not MIN_VIEWS<=len(views)<=MAX_VIEWS):
        raise ValueError("Choose 2-9 private research camera views")
    parsed=[]
    for item in views:
        if type(item) is str:
            camera=parse_view(item)
        elif type(item) in (tuple,list) and len(item)==3:
            camera=validated_camera(*item)
        else:
            raise ValueError("Malformed camera choice")
        if camera in parsed:
            raise ValueError("Repeated camera cannot count as distinct view")
        parsed.append(camera)
    return tuple(parsed)


def safe_frame_pixels(frame:Path):
    st=frame.lstat()
    if not frame.is_file() or frame.is_symlink() or st.st_size!=IMAGE_BYTES:
        raise ValueError("Private research PPM frame changed")
    raw=frame.read_bytes()
    if len(raw)!=IMAGE_BYTES or not raw.startswith(HEADER):
        raise ValueError("Invalid private research PPM")
    return raw[len(HEADER):]


def build_contact_sheet(frames,output:Path):
    count=len(frames)
    if count<MIN_VIEWS or count>MAX_VIEWS:
        raise ValueError("Invalid number of research camera frames")
    columns=min(3,count)
    rows=(count+columns-1)//columns
    width=columns*W
    height=rows*H
    size=width*height*3
    if size>MAX_SHEET_BYTES:
        raise ValueError("Research sheet exceeds private memory budget")
    # C wireframe background in RGB format.
    canvas=bytearray(b"\x25\x1c\x18"*(width*height))
    for i,frame in enumerate(frames):
        raw=safe_frame_pixels(frame)
        top=(i//columns)*H
        left=(i%columns)*W
        for line in range(H):
            start=((top+line)*width+left)*3
            src=line*W*3
            canvas[start:start+W*3]=raw[src:src+W*3]
    # The user-facing images and settings remain private, not printed.
    header=f"P6\n{width} {height}\n255\n".encode("ascii")
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"wb") as file:
            fd=-1
            file.write(header)
            file.write(canvas)
    finally:
        if fd>=0:
            os.close(fd)
    return (width,height)


def preview(rig:Path,primary:Path,secondary:Path|None,
            output:Path,views):
    safe_destination(output)
    cameras=validate_views(views)
    # Reuse the exact private content-intake and independent pose check
    # of Stage203. No original resource bytes enter this source tree.
    rig_raw=bounded_read(rig,MAX_RIG_FILE)
    anim_raw=bounded_read(primary,MAX_ANIM_FILE)
    alt_raw=(bounded_read(secondary,MAX_ANIM_FILE)
             if secondary is not None else None)
    inspect_pose_envelope(rig_raw,anim_raw,alt_raw)
    old_umask=os.umask(0o077)
    made=False
    try:
        output.mkdir(mode=0o700)
        made=True
        staged=output/"private-switch-sd"
        details=prepare(staged,rig,primary,secondary)
        pairs=(
            (staged/"switch/foj/rig/preview.fojrm",rig_raw),
            (staged/"switch/foj/anims/preview.banim",anim_raw),
        )
        for path,original in pairs:
            if path.read_bytes()!=original:
                raise ValueError("Local source changed during camera preview")
        if alt_raw is not None and (
            staged/"switch/foj/anims/preview_b.banim"
        ).read_bytes()!=alt_raw:
            raise ValueError("Local optional clip changed during preview")

        executable=output/"private-actor-host-smoke"
        compile_host(executable)
        all_views=output/"private-camera-frames"
        all_views.mkdir(mode=0o700)
        selected=[]
        records=[]
        for i,camera in enumerate(cameras):
            folder=all_views/f"view-{i:02d}"
            folder.mkdir(mode=0o700)
            native=run_native(executable,staged,folder,camera=camera)
            report=render_evidence(
                folder,secondary=alt_raw is not None
            )
            if native["rig_bone_count"]!=details["rig_bone_count"] or (
                native["secondary_clip_used"] is not (alt_raw is not None)
            ):
                raise ValueError("Native rig/clip intake disagreement")
            selected.append(folder/(PREVIEW_FRAME+".ppm"))
            records.append({
                "view_index":i,
                "yaw_radians":camera[0],
                "pitch_radians":camera[1],
                "zoom_factor":camera[2],
                "frames_generated":report["private_frames_count"],
                "pause_reset_zero_weight_consistent":
                    report["pause_reset_zero_weight_consistent"],
                "original_ps3_camera_authenticated":False,
            })
        width,height=build_contact_sheet(
            selected,output/"private-camera-contact-sheet.ppm"
        )
        protected_json(output/"private-camera-view-index.json",{
            "schema":SCHEMA,
            "contact_sheet_preview_state":PREVIEW_FRAME,
            "tile_width":W,
            "tile_height":H,
            "contact_sheet_width":width,
            "contact_sheet_height":height,
            "view_order":records,
            "source_game_camera_match_verified":False,
            "original_ps3_pose_accuracy_verified":False,
            "actual_nintendo_switch_execution_verified":False,
        })
        return {
            "schema":SCHEMA,
            "local_private_comparison_created":True,
            "views_rendered":len(cameras),
            "native_frames_rendered":len(cameras)*len(STATES),
            "private_contact_sheet_generated":True,
            "private_camera_values_or_images_uploaded":False,
            "source_game_camera_match_verified":False,
            "original_ps3_animation_fidelity_verified":False,
            "warning":(
                "Multiple research projections are visual alternatives "
                "only, not original PS3 camera recovery or verified "
                "gameplay animation reconstruction."
            ),
        }
    except BaseException:
        if made:
            shutil.rmtree(output)
        raise
    finally:
        os.umask(old_umask)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig",required=True,type=Path)
    parser.add_argument("--primary",required=True,type=Path)
    parser.add_argument("--secondary",type=Path)
    parser.add_argument("--camera",action="append",required=True,
                        help="Private yaw,pitch,zoom tuple; repeat 2-9 times")
    parser.add_argument("--output-root",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        result=preview(
            args.rig,args.primary,args.secondary,args.output_root,args.camera
        )
    except (OSError,ValueError,TypeError,OverflowError,IndexError,
            RuntimeError,ArithmeticError):
        print("Private Stage214 multi-camera preview rejected.",
              file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
