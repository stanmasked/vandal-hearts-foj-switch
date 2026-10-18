#!/usr/bin/env python3
"""Prepare an owner-LOCAL SD directory for actual rig/dual-BANIM research.

Never network-access, add original PS3 materials to Git, zip, or print
original asset paths/hashes/transforms. Accept only verified compatible
FOJRM001/BANIM files. A missing secondary means single-clip research.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from tools.check_local_rig_clip_set import inspect_clip_set, bounded_read
from tools.check_local_rig_pair import MAX_RIG_FILE, MAX_ANIM_FILE

SCHEMA="foj.stage200.private_sd_directory_v1"


def private_write(path: Path, content: bytes) -> None:
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"wb") as out:
            fd=-1
            out.write(content)
    finally:
        if fd>=0:
            os.close(fd)


def prepare(root: Path, mesh: Path, first: Path,
            secondary: Path | None = None) -> dict:
    if root.exists() or root.is_symlink() or not root.parent.is_dir():
        raise ValueError("Destination must be a new private directory")
    rig=bounded_read(mesh,MAX_RIG_FILE)
    anim=bounded_read(first,MAX_ANIM_FILE)
    alt=bounded_read(secondary,MAX_ANIM_FILE) if secondary else None
    assessment=inspect_clip_set(rig,anim,alt)
    if not assessment["primary_hierarchy_match"] or (
        alt is not None and not assessment["secondary_hierarchy_match"]
    ):
        raise ValueError("Animation parent hierarchy mismatched")
    root.mkdir(mode=0o700)
    try:
        switch=root/"switch"
        game=switch/"foj"
        rigdir=game/"rig"
        animdir=game/"anims"
        for folder in (switch,game,rigdir,animdir):
            folder.mkdir(mode=0o700)
        private_write(rigdir/"preview.fojrm",rig)
        private_write(animdir/"preview.banim",anim)
        if alt is not None:
            private_write(animdir/"preview_b.banim",alt)
    except (OSError,ValueError):
        # Clean up only this newly-created destination; never modify inputs
        # or touch any unrelated existing private directory.
        shutil.rmtree(root)
        raise
    return {
        "schema":SCHEMA,
        "mode":"private_user_local_only",
        "files_staged":3 if alt is not None else 2,
        "rig_bone_count":assessment["bone_count"],
        "rig_vertex_count":assessment["vertex_count"],
        "secondary_clip_accepted":alt is not None,
        "actual_original_ps3_asset_identity_verified":False,
        "real_ps3_animation_matrix_convention_verified":False,
        "physical_nintendo_switch_playback_verified":False,
        "original_asset_paths_printed":False,
        "original_asset_bytes_published":False,
        "warning":(
            "Private game-derived bytes are now stored only in the "
            "specified local directory. Do not commit, share, archive, "
            "or attach this directory to GitHub Actions."
        ),
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh",type=Path)
    parser.add_argument("primary",type=Path)
    parser.add_argument("--secondary",type=Path)
    parser.add_argument("--output-root",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        result=prepare(args.output_root,args.mesh,args.primary,args.secondary)
    except (ValueError,OSError):
        print("Private Stage 200 SD preparation rejected. Review locally.",
              file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
