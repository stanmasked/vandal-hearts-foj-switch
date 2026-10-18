#!/usr/bin/env python3
"""Stage215: owner-only lock of a chosen Stage214 camera to Stage203 frames.

The exact research render is pinned *before* annotating original-game
captures. It is not an attestation of genuine PS3 source gameplay or of
the camera being correct. Lock receipts stay local and must not be
uploaded to public CI or GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys

from tools.check_local_rig_pair import MAX_RIG_FILE,MAX_ANIM_FILE
from tools.foj_stage196_private_pose_observations import (
    only_keys,private_read,rejected
)
from tools.foj_stage203_private_actor_evidence import (
    HEADER,IMAGE_BYTES,W,H,STATES,
    render_evidence,safe_destination,validated_camera
)
from tools.foj_stage214_private_multicamera_preview import (
    SCHEMA as PREVIEW_SCHEMA,
    MIN_VIEWS,MAX_VIEWS,PREVIEW_FRAME,safe_frame_pixels
)

SCHEMA="foj.stage215.private_camera_lock.v2"
REPORT="foj.stage215.private_camera_lock_check.v1"
MAX_CONTACT_SHEET_BYTES=4_200_000
SHA_KEYS=("initial","play_025","paused","fade_0","fade_025",
          "fade_050","fade_075","fade_done","reset")


def camera_index(preview_root:Path,chosen:int):
    record=private_read(preview_root/"private-camera-view-index.json")
    only_keys(record,{
        "schema","contact_sheet_preview_state","tile_width","tile_height",
        "contact_sheet_width","contact_sheet_height","view_order",
        "source_game_camera_match_verified",
        "original_ps3_pose_accuracy_verified",
        "actual_nintendo_switch_execution_verified"
    })
    rows=record["view_order"]
    if (record["schema"]!=PREVIEW_SCHEMA or
        record["contact_sheet_preview_state"]!=PREVIEW_FRAME or
        type(rows) is not list or
        not MIN_VIEWS<=len(rows)<=MAX_VIEWS or
        type(chosen) is not int or not 0<=chosen<len(rows) or
        record["tile_width"]!=W or record["tile_height"]!=H or
        record["contact_sheet_width"]!=W*min(3,len(rows)) or
        record["contact_sheet_height"]!=H*math.ceil(len(rows)/3) or
        any(record[k] is not False for k in (
            "source_game_camera_match_verified",
            "original_ps3_pose_accuracy_verified",
            "actual_nintendo_switch_execution_verified"
        ))):
        raise rejected()
    cameras=[]
    for i,row in enumerate(rows):
        only_keys(row,{
            "view_index","yaw_radians","pitch_radians","zoom_factor",
            "frames_generated","pause_reset_zero_weight_consistent",
            "original_ps3_camera_authenticated"
        })
        if (type(row["view_index"]) is not int or row["view_index"]!=i or
            row["frames_generated"]!=len(STATES) or
            row["pause_reset_zero_weight_consistent"] is not True or
            row["original_ps3_camera_authenticated"] is not False):
            raise rejected()
        camera=validated_camera(
            row["yaw_radians"],row["pitch_radians"],row["zoom_factor"]
        )
        if camera in cameras:
            raise rejected()
        cameras.append(camera)
    return cameras,record


def bound_private_ppm(path:Path):
    st=path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_size!=IMAGE_BYTES
        or path.is_symlink()):
        raise rejected()
    with path.open("rb") as stream:
        raw=stream.read(IMAGE_BYTES+1)
    if len(raw)!=IMAGE_BYTES or not raw.startswith(HEADER):
        raise rejected()
    return raw


def staged_source_witness(root:Path):
    """Private hashes bind the exact native C input bytes across both runs.

    Never include private source paths or content in public CLI output.
    Reject symlinks (including dangling links), directories and files
    larger than the original local-intake limits.
    """
    staged=root/"private-switch-sd"/"switch/foj"
    def digest(path:Path,limit:int):
        # Read from a single no-follow descriptor: a pathname swap between
        # lstat() and read_bytes() must not redirect a checked local asset.
        # Nonblocking open prevents hanging on a substituted FIFO.
        fd=-1
        try:
            fd=os.open(path,os.O_RDONLY | getattr(os,"O_NOFOLLOW",0)
                       | getattr(os,"O_NONBLOCK",0))
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or not 1<=st.st_size<=limit:
                raise rejected()
            with os.fdopen(fd,"rb") as stream:
                fd=-1
                raw=stream.read(limit+1)
            if len(raw)!=st.st_size:
                raise rejected()
            return hashlib.sha256(raw).hexdigest()
        except (OSError,ValueError):
            raise rejected() from None
        finally:
            if fd>=0:
                os.close(fd)
    optional=staged/"anims/preview_b.banim"
    return {
        "rig":digest(staged/"rig/preview.fojrm",MAX_RIG_FILE),
        "primary":digest(staged/"anims/preview.banim",MAX_ANIM_FILE),
        "secondary":(
            digest(optional,MAX_ANIM_FILE)
            if optional.exists() or optional.is_symlink() else None
        ),
    }


def preview_witness(preview_root:Path,chosen:int):
    if not preview_root.is_dir() or preview_root.is_symlink():
        raise rejected()
    cameras,record=camera_index(preview_root,chosen)
    n=len(cameras)
    columns=min(n,3)
    rows=math.ceil(n/3)
    sw=columns*W
    sh=rows*H
    header=f"P6\n{sw} {sh}\n255\n".encode("ascii")
    contact=preview_root/"private-camera-contact-sheet.ppm"
    st=contact.lstat()
    if (not stat.S_ISREG(st.st_mode) or contact.is_symlink() or
        st.st_size!=len(header)+sw*sh*3 or
        st.st_size>MAX_CONTACT_SHEET_BYTES):
        raise rejected()
    content=contact.read_bytes()
    if not content.startswith(header) or len(content)!=st.st_size:
        raise rejected()
    body=content[len(header):]
    # Reject sheet tiles that differ from the actual C-frame pixels.
    # Keep entire image bytes in memory; output only a PRIVATE hash.
    for i in range(n):
        folder=preview_root/"private-camera-frames"/f"view-{i:02d}"
        render_evidence(folder,secondary=(
            (preview_root/"private-switch-sd"/
             "switch/foj/anims/preview_b.banim").is_file()
        ))
        frame=safe_frame_pixels(folder/(PREVIEW_FRAME+".ppm"))
        for y in range(H):
            start=((i//3)*H+y)*sw*3+(i%3)*W*3
            if body[start:start+W*3]!=frame[y*W*3:(y+1)*W*3]:
                raise rejected()
    # Unused contact-sheet tiles must be exact Stage214 background.
    for i in range(n,columns*rows):
        for y in range(H):
            start=((i//3)*H+y)*sw*3+(i%3)*W*3
            if body[start:start+W*3]!=b"\x25\x1c\x18"*W:
                raise rejected()
    selected=preview_root/"private-camera-frames"/f"view-{chosen:02d}"
    frame_sha={}
    for name in SHA_KEYS:
        frame_sha[name]=hashlib.sha256(
            bound_private_ppm(selected/(name+".ppm"))
        ).hexdigest()
    return {
        "schema":SCHEMA,
        "view_index":chosen,
        "camera_yaw_radians":cameras[chosen][0],
        "camera_pitch_radians":cameras[chosen][1],
        "camera_zoom_factor":cameras[chosen][2],
        "preview_sheet_sha256_private":
            hashlib.sha256(content).hexdigest(),
        "native_frame_sha256_private":frame_sha,
        "staged_source_sha256_private":staged_source_witness(preview_root),
        "owner_selected_camera_not_automatically_ranked":True,
        "original_ps3_camera_authenticated":False,
        "original_game_animation_fidelity_verified":False,
    }


def lock_choice(preview_root:Path,selected:int,destination:Path):
    safe_destination(destination)
    data=preview_witness(preview_root,selected)
    fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as handle:
            fd=-1
            json.dump(data,handle,indent=2,sort_keys=True)
            handle.write("\n")
    finally:
        if fd>=0:
            os.close(fd)
    return {
        "schema":REPORT,
        "operator_camera_choice_locked_privately":True,
        "rendered_frames_pinned":len(STATES),
        "source_game_camera_match_verified":False,
        "original_animation_fidelity_verified":False,
    }


def verify_choice(preview_root:Path,lock_file:Path,stage203_root:Path):
    lock=private_read(lock_file)
    only_keys(lock,{
        "schema","view_index",
        "camera_yaw_radians","camera_pitch_radians","camera_zoom_factor",
        "preview_sheet_sha256_private","native_frame_sha256_private",
        "staged_source_sha256_private",
        "owner_selected_camera_not_automatically_ranked",
        "original_ps3_camera_authenticated",
        "original_game_animation_fidelity_verified"
    })
    if (lock["schema"]!=SCHEMA or
        lock["owner_selected_camera_not_automatically_ranked"] is not True or
        lock["original_ps3_camera_authenticated"] is not False or
        lock["original_game_animation_fidelity_verified"] is not False):
        raise rejected()
    latest=preview_witness(preview_root,lock["view_index"])
    if latest!=lock:
        raise rejected()
    settings=private_read(stage203_root/"private-research-camera.json")
    only_keys(settings,{
        "schema","yaw_radians","pitch_radians","zoom_factor",
        "operator_adjustable_research_projection",
        "camera_parameters_supplied_to_native_c_render",
        "original_ps3_camera_authenticated",
        "source_game_view_equivalence_verified"
    })
    if (settings["schema"]!="foj.stage213.private_research_projection.v1"
        or settings["original_ps3_camera_authenticated"] is not False
        or settings["source_game_view_equivalence_verified"] is not False
        or settings["camera_parameters_supplied_to_native_c_render"] is not True):
        raise rejected()
    camera=validated_camera(
        settings["yaw_radians"],settings["pitch_radians"],
        settings["zoom_factor"]
    )
    selected_camera=(
        lock["camera_yaw_radians"],lock["camera_pitch_radians"],
        lock["camera_zoom_factor"]
    )
    if camera!=selected_camera:
        raise rejected()
    if staged_source_witness(stage203_root)!=lock["staged_source_sha256_private"]:
        raise rejected()
    frames=stage203_root/"private-frames"
    render_evidence(
        frames,secondary=(stage203_root/"private-switch-sd"/
            "switch/foj/anims/preview_b.banim").is_file()
    )
    for name in SHA_KEYS:
        raw=bound_private_ppm(frames/(name+".ppm"))
        if hashlib.sha256(raw).hexdigest()!=lock[
            "native_frame_sha256_private"
        ][name]:
            raise rejected()
    # The lock is an owner's local identity check, not independent
    # evidence of source camera or original animation correctness.
    return {
        "schema":REPORT,
        "owner_private_choice_and_final_native_c_frames_exactly_match":True,
        "matched_native_frames":len(STATES),
        "camera_parameters_exactly_equal":True,
        "view_image_bytes_or_hashes_exported":False,
        "source_game_camera_match_verified":False,
        "original_animation_fidelity_verified":False,
        "warning":(
            "Exact matching of private native C wireframes across two "
            "local runs does not prove PS3 camera, actor, clip identity "
            "or fidelity to the original game."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--lock",action="store_true")
    mode.add_argument("--verify",action="store_true")
    parser.add_argument("--preview-root",type=Path,required=True)
    parser.add_argument("--lock-file",type=Path,required=True)
    parser.add_argument("--view-index",type=int)
    parser.add_argument("--stage203-root",type=Path)
    args=parser.parse_args(argv)
    try:
        if args.lock:
            if args.view_index is None or args.stage203_root is not None:
                raise rejected()
            result=lock_choice(
                args.preview_root,args.view_index,args.lock_file
            )
        else:
            if args.view_index is not None or args.stage203_root is None:
                raise rejected()
            result=verify_choice(
                args.preview_root,args.lock_file,args.stage203_root
            )
    except (OSError,ValueError,TypeError,IndexError,OverflowError):
        print("Private Stage215 research-camera lock rejected.",
              file=sys.stderr)
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
