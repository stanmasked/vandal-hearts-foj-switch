#!/usr/bin/env python3
"""Stage274 negative guest: mutate one invented opaque rear DDS alpha byte.

Only creates a fresh synthetic SD root. No original PS3 resources or user
assets are read, copied or uploaded. Not an actual NeXium result.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from tools.foj_stage273_dynamic_gpu_sd import install_dynamic
from tools.foj_stage267_generated_multiblend_sd import SUBDIR
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import COOL

SCHEMA="foj.stage274.native_rear_alpha_negative.v1"
EXPECTED_MARKER="FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1"
PNG_HEADER_BYTES=128


def prepare_negative(root:Path,shaders:Path)->dict:
    root=Path(root)
    # The same generator validates that this root does not exist.
    receipt=install_dynamic(root,shaders,"original")
    atlas=root/SUBDIR/"material2.dds"
    if atlas.is_symlink() or not atlas.is_file():
        raise ValueError("Unsafe generated rear DDS path")
    before=atlas.read_bytes()
    reference=generated_dds((*COOL,255))
    if before!=reference or len(before)!=PNG_HEADER_BYTES+64*64*4:
        raise ValueError("Unexpected generated rear atlas layout")
    altered=bytearray(before)
    at=PNG_HEADER_BYTES+3
    if altered[at]!=255:
        raise ValueError("Generated rear pixel not initially opaque")
    altered[at]=254
    if sum(a!=b for a,b in zip(before,altered))!=1:
        raise ValueError("Negative fixture did not change exactly one byte")
    atlas.write_bytes(altered)
    if any((root/SUBDIR/name).exists() for name in
           ("foj-native-rear-alpha-reject.txt",
            "foj-native-sort-pass.txt","foj-native-alpha-pass.txt")):
        raise ValueError("Native guest marker was unexpectedly pre-created")
    receipt.update({
        "schema":SCHEMA,
        "scenario":"one-rear-alpha-254",
        "changed_file":"material2.dds",
        "changed_bytes":1,
        "original_alpha":255,
        "mutated_alpha":254,
        "expected_native_rejection_marker":EXPECTED_MARKER,
        "guest_verified":False,
        "generated_only":True,
        "original_ps3_resources":False,
    })
    return receipt


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--shaders",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(prepare_negative(args.data_root,args.shaders),
                         sort_keys=True))
    except (ValueError,OSError) as error:
        print("Stage274 negative DDS refused: "+str(error),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
