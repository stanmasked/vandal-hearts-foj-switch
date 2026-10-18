#!/usr/bin/env python3
"""Stage 203: owner-OFFLINE end-to-end original-capable actor evidence.

Runs the Stage200 production C parser/player/skinning/wireframe against the
owner's locally supplied FOJRM001 + BANIM(s) and independently evaluates
the Stage195 private pose envelope. Optional *operator annotated* PS3
landmark observations are analyzed separately; not authenticated.

NO assets, screenshots, transform arrays, local paths or hashes printed.
Never call this with real game assets on public CI or upload the output.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

from tools.check_local_rig_clip_set import bounded_read
from tools.check_local_rig_pair import MAX_RIG_FILE, MAX_ANIM_FILE
from tools.foj_stage195_private_pose_envelope import inspect_pose_envelope
from tools.foj_stage196_private_pose_observations import (
    align_observations, private_read
)
from tools.foj_stage197_private_motion_lag import compare as lag_compare
from tools.foj_stage198_motion_ambiguity import inspect as ambiguity_inspect
from tools.foj_stage199_private_multiwindow import _read as multi_read, evaluate
from tools.foj_stage200_prepare_private_sd import prepare

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="foj.stage203.private_actor_evidence.v1"
W,H=480,320
HEADER=b"P6\n480 320\n255\n"
IMAGE_BYTES=len(HEADER)+W*H*3
STATES=(
    "initial","play_025","paused","fade_0","fade_025",
    "fade_050","fade_075","fade_done","reset",
)
SOURCES=(
    "tools/foj_stage200_actor_host_smoke.c",
    "core/rigged_actor_session.c","core/anim_player.c",
    "core/rigmesh_io.c","core/banim_core.c",
    "core/skeletal_skin.c","core/obj_wireframe.c",
)


def safe_destination(root:Path):
    # New destination, never an existing directory or any public repo path.
    if root.exists() or root.is_symlink():
        raise ValueError("Never overwrite existing private evidence")
    parent=root.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError("Private evidence parent must be an existing real dir")
    if not root.name or root.name in (".",".."):
        raise ValueError("Invalid private output directory")
    resolved=root.resolve()
    repo=ROOT.resolve()
    if resolved.is_relative_to(repo) and not resolved.is_relative_to(
        repo/"local-data"
    ):
        raise ValueError("Repository evidence must be under ignored local-data")


def protected_json(path:Path, record:dict):
    # No file overwrites and no accidental world-readable evidence.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as output:
            json.dump(record,output,sort_keys=True,indent=2,allow_nan=False)
            output.write("\n")
    finally:
        pass


def compile_host(executable:Path):
    compiler=shutil.which("cc")
    if not compiler:
        raise ValueError("C11 compiler not available")
    command=[
        compiler,"-std=c11","-O2","-Wall","-Wextra","-Werror",
        "-pedantic","-Icore",*SOURCES,"-lm","-o",str(executable),
    ]
    result=subprocess.run(command,cwd=ROOT,capture_output=True,
                          timeout=45,check=False)
    if result.returncode!=0 or not executable.is_file():
        raise ValueError("Native research compiler rejected source")


def run_native(executable:Path,sd_root:Path,output:Path):
    result=subprocess.run(
        [str(executable),str(sd_root),str(output)],
        cwd=ROOT,capture_output=True,timeout=45,check=False,
    )
    if result.returncode!=0 or result.stderr:
        raise ValueError("Native actor playback rejected local pair")
    if len(result.stdout)>2048:
        raise ValueError("Unexpected native diagnostic output")
    record=json.loads(result.stdout)
    if type(record) is not dict or record.get("schema")!=(
        "foj.stage200.local_actor_host_smoke.v1"
    ) or record.get("frames_rendered")!=9 or (
        record.get("original_ps3_animation_verified") is not False
    ):
        raise ValueError("Unexpected native report schema")
    return record


def render_evidence(folder:Path,*,secondary:bool):
    names={x.name for x in folder.iterdir()}
    if names!={name+".ppm" for name in STATES}:
        raise ValueError("Missing or unexpected private frames")
    pixels={}
    wire=b"\xda\xe4\xbd"
    for label in STATES:
        path=folder/(label+".ppm")
        st=path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_size!=IMAGE_BYTES:
            raise ValueError("Private frame is not a bounded PPM")
        content=path.read_bytes()
        if len(content)!=IMAGE_BYTES or not content.startswith(HEADER):
            raise ValueError("Malformed native frame")
        payload=content[len(HEADER):]
        if payload.count(wire)<6:
            raise ValueError("Native frame does not contain expected wire")
        pixels[label]=payload
    # Strong invariants that hold regardless of animation activity.
    for left,right in (
        ("initial","reset"),
        ("initial","fade_0"),
        ("play_025","paused"),
    ):
        if pixels[left]!=pixels[right]:
            raise ValueError("Pause/reset/zero-alpha geometric invariant failed")
    # A user-owned idle clip can legitimately have static silhouettes.
    # Never reject valid data solely for low observable motion.
    def changed(a,b):
        x,y=pixels[a],pixels[b]
        return sum(x[i:i+3]!=y[i:i+3] for i in range(0,len(x),3))
    a_motion=changed("initial","play_025")
    fade_values=[
        changed(a,b) for a,b in zip(
            ("fade_0","fade_025","fade_050","fade_075"),
            ("fade_025","fade_050","fade_075","fade_done"),
        )
    ]
    return {
        "schema":"foj.stage203.private_frame_consistency.v1",
        "private_frames_count":len(STATES),
        "frame_width":W,
        "frame_height":H,
        "pause_reset_zero_weight_consistent":True,
        "primary_pose_changed_pixels":a_motion,
        "successive_fade_changed_pixels":fade_values,
        "secondary_clip_present":secondary,
        "primary_pose_motion_observed":a_motion>0,
        "secondary_fade_motion_observed":secondary and any(fade_values),
        "private_images_uploaded":False,
        "original_ps3_visual_fidelity_verified":False,
        "physical_switch_execution_verified":False,
    }


def observations_if_any(path:Path|None,folder:Path):
    if path is None:
        return {
            "operator_annotations_supplied":False,
            "original_ps3_comparison_status":"not_performed",
        }
    document=private_read(path)
    shape=align_observations(document)
    protected_json(folder/"private-operator-shape-comparison.json",shape)
    result={
        "operator_annotations_supplied":True,
        "original_ps3_comparison_status":"operator_annotations_compared_only",
        "operator_declared_both_captures_recorded":
            shape["operator_declared_both_captures_recorded"],
        "original_ps3_capture_authenticated":False,
        "annotations_proven_to_match_generated_frames":False,
    }
    # Stage197/198 need >=8 frames with pose movement, unlike Stage196.
    if len(document["frames"])>=8:
        try:
            timing=lag_compare(document)
            robust=ambiguity_inspect(document)
        except (ValueError,OverflowError,ZeroDivisionError):
            result["timing_diagnostic"]="unavailable_for_input_motion"
        else:
            protected_json(folder/"private-operator-timing.json",timing)
            protected_json(folder/"private-operator-timing-robustness.json",
                           robust)
            result["timing_diagnostic"]=robust["robustness_adjusted_verdict"]
    else:
        result["timing_diagnostic"]="requires_eight_or_more_frames"
    return result


def conduct(rig:Path,primary:Path,secondary:Path|None,
            output:Path,*,observations:Path|None=None,
            multiwindow:Path|None=None):
    safe_destination(output)
    # Strictly bounded source reads and independent source-coordinate
    # research math happen BEFORE creating ANY private output.
    rig_bytes=bounded_read(rig,MAX_RIG_FILE)
    primary_bytes=bounded_read(primary,MAX_ANIM_FILE)
    secondary_bytes=(bounded_read(secondary,MAX_ANIM_FILE)
                     if secondary is not None else None)
    envelope=inspect_pose_envelope(
        rig_bytes,primary_bytes,secondary_bytes
    )
    # Reject bad private operator input before starting native rendering.
    if observations is not None:
        align_observations(private_read(observations))
    if multiwindow is not None:
        evaluate(multi_read(multiwindow))
    old_umask=os.umask(0o077)
    output_created=False
    try:
        output.mkdir(mode=0o700)
        output_created=True
        stage=prepare(output/"private-switch-sd",rig,primary,secondary)
        sd=output/"private-switch-sd"
        # Source inputs may be changed by other software mid-run. Check
        # exact byte-for-byte identity, but emit NO hashes, bytes or names.
        if (sd/"switch/foj/rig/preview.fojrm").read_bytes()!=rig_bytes or (
            sd/"switch/foj/anims/preview.banim").read_bytes()!=primary_bytes
        ):
            raise ValueError("Local resource changed during evidence capture")
        if secondary_bytes is not None and (
            sd/"switch/foj/anims/preview_b.banim"
        ).read_bytes()!=secondary_bytes:
            raise ValueError("Second local animation changed during capture")

        executable=output/"private-actor-host-smoke"
        compile_host(executable)
        frames=output/"private-frames"
        frames.mkdir(mode=0o700)
        native=run_native(executable,sd,frames)
        frame_report=render_evidence(
            frames,secondary=secondary_bytes is not None
        )
        if (native["secondary_clip_used"] is not (
            secondary_bytes is not None
        )) or native["rig_bone_count"]!=envelope["bone_count"]:
            raise ValueError("Native and Python resource intake disagree")
        protected_json(output/"private-pose-envelope.json",envelope)
        protected_json(output/"private-render-evidence.json",frame_report)
        observed=observations_if_any(observations,output)
        if multiwindow is None:
            multi={
                "independent_windows_submitted":False,
                "multiwindow_comparison_status":"not_performed",
            }
        else:
            details=evaluate(multi_read(multiwindow))
            protected_json(output/"private-multiwindow-report.json",details)
            multi={
                "independent_windows_submitted":True,
                "multiwindow_comparison_status":
                    details["diagnosis"],
                "window_independence_authenticated":False,
            }
        report={
            "schema":SCHEMA,
            "scope":"owner_machine_private_only",
            "actor_file_intake_hierarchy_compatible":True,
            "rig_bone_count":stage["rig_bone_count"],
            "rig_vertex_count":stage["rig_vertex_count"],
            "private_frames":frame_report["private_frames_count"],
            "secondary_clip_staged":stage["secondary_clip_accepted"],
            "private_host_render_succeeded":True,
            "research_bind_identity_checked":True,
            "primary_motion_observed_in_private_frames":
                frame_report["primary_pose_motion_observed"],
            "secondary_motion_observed_in_private_frames":
                frame_report["secondary_fade_motion_observed"],
            **observed,
            **multi,
            "asset_identity_authenticated_as_original_ps3":False,
            "original_game_animation_accuracy_verified":False,
            "actual_original_ps3_capture_authenticated":False,
            "nexium_execution_tested_by_this_run":False,
            "physical_switch_tested":False,
            "private_output_never_upload_automatically":True,
            "warning":(
                "Compatibility and native execution do not prove that "
                "supplied rig and clips are authentic, matched original "
                "PS3 animations or rendered with correct game-engine math. "
                "Keep complete output, including reports, OFF GitHub."
            ),
        }
        protected_json(output/"private-evidence-status.json",report)
        return report
    except BaseException:
        # Newly created output only; do not preserve partial game-derived
        # data or diagnostic frames from a rejected operation.
        if output_created:
            shutil.rmtree(output)
        raise
    finally:
        os.umask(old_umask)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rig",required=True,type=Path)
    parser.add_argument("--primary",required=True,type=Path)
    parser.add_argument("--secondary",type=Path)
    parser.add_argument("--output-root",required=True,type=Path)
    parser.add_argument("--observations",type=Path)
    parser.add_argument("--multiwindow",type=Path)
    args=parser.parse_args(argv)
    try:
        result=conduct(
            args.rig,args.primary,args.secondary,args.output_root,
            observations=args.observations,multiwindow=args.multiwindow,
        )
    except (OSError,ValueError,TypeError,RuntimeError,
            subprocess.SubprocessError,OverflowError,IndexError,
            ZeroDivisionError,json.JSONDecodeError):
        print("Private Stage203 actor evidence rejected; inspect locally.",
              file=sys.stderr)
        return 2
    # No user asset path, hash, bone arrays, image data or source metrics
    # in stdout; real aggregate metrics are PRIVATE FILES only.
    print(json.dumps({
        "schema":SCHEMA,
        "private_local_run_succeeded":True,
        "frames_generated":result["private_frames"],
        "secondary_clip_staged":result["secondary_clip_staged"],
        "operator_annotations_supplied":
            result["operator_annotations_supplied"],
        "original_game_animation_accuracy_verified":False,
        "no_original_resources_uploaded_by_this_tool":True,
    },sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
