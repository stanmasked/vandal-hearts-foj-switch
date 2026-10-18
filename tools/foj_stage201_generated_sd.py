#!/usr/bin/env python3
"""Create an isolated NeXium SD root from generated-only FoJ fixtures.

FOR CI ONLY. Refuses existing roots and cannot ingest paths to user/game data.
The FOJRM001 and two BANIMs derive exclusively from generated unit fixtures.
No original PS3 resources, hashes, textures or screenshot data are embedded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

from tests.test_decode_rig_banim import synthetic_banim, synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.export_local_rigmesh import pack_rig_mesh
from tools.foj_stage200_prepare_private_sd import prepare

SCHEMA="foj.stage201.generated_nexium_sd.v1"


def generated_actors():
    model=synthetic_complete_model()[:-4]+synthetic_rig()
    mesh,_=pack_rig_mesh(model)
    primary=synthetic_banim()
    alternative=bytearray(primary)
    struct.pack_into("<f",alternative,11+5+1+4+16,.25)
    return mesh,primary,bytes(alternative)


def install_generated_sd(data_root: Path) -> dict:
    if data_root.exists() or data_root.is_symlink():
        raise ValueError("Refusing existing emulator data root")
    if not data_root.parent.is_dir() or data_root.parent.is_symlink():
        raise ValueError("Emulator data parent must be a real directory")
    mesh,primary,secondary=generated_actors()
    # No system or owner-held game resource paths accepted. Everything
    # installed is created from invented public synthetic fixture builders.
    data_root.mkdir(mode=0o700)
    try:
        result=prepare(data_root/"sdmc",
                       *_materialize_fixture_bytes(data_root,mesh,primary,secondary))
        # Stage200 package's temporary source directory is removed below.
        temporary=data_root/"generated-only-fixtures"
        for child in temporary.iterdir():
            child.unlink()
        temporary.rmdir()
    except BaseException:
        # Avoid leaving a partially staged directory in CI on error.
        import shutil
        import os
        if data_root.is_dir() and not data_root.is_symlink():
            shutil.rmtree(data_root)
        raise
    return {
        "schema":SCHEMA,
        "fixture_type":"generated_only_no_original_ps3_content",
        "sd_relative_root":"sdmc/switch/foj",
        "rig_bone_count":result["rig_bone_count"],
        "rig_vertex_count":result["rig_vertex_count"],
        "generated_clip_count":2,
        "nexium_guest_fsp_mount_proven":False,
        "nexium_guest_animation_rendered":False,
        "original_game_assets_used":False,
        "physical_switch_tested":False,
    }


def _materialize_fixture_bytes(data_root: Path,mesh,primary,secondary):
    folder=data_root/"generated-only-fixtures"
    folder.mkdir(mode=0o700)
    paths=tuple(folder/name for name in
                ("synthetic.fojrm","synthetic_a.banim","synthetic_b.banim"))
    for path,content in zip(paths,(mesh,primary,secondary),strict=True):
        path.write_bytes(content)
    return paths


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root",type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=install_generated_sd(args.data_root)
    except (ValueError,OSError,OverflowError,IndexError):
        print("Generated NeXium SD setup rejected.",file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
