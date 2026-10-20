#!/usr/bin/env python3
"""Stage274 independent final evidence audit for deko3d GPU state.

Only a real separate NeXium guest invoked by GitHub Actions establishes
the guest-origin of receipts or pixels; synthetic host tests do not.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from tools.foj_stage273_dynamic_gpu_check import verify as verify_frames
from tools.foj_stage273_dynamic_gpu_sd import CASES, BACK_TO_FRONT

SCHEMA="foj.stage274.real_gpu_pass_state.v1"


def expected_receipt(case:str)->bytes:
    if case not in CASES:
        raise ValueError("Unknown alpha pass case")
    order=BACK_TO_FRONT[case]
    groups=[]
    for pos,material in enumerate(order):
        groups.append(f"{material}:{int(pos!=0)}:1:{int(pos==0)}")
    return ("FOJ_NATIVE_ALPHA_PASS_V1 "+" ".join(groups)+"\n").encode("ascii")


def verify(root:Path)->dict:
    root=Path(root)
    # Stage273's independent GPU oracle requires four actual RGB frames,
    # phase changes, matching overlap/rear-only colors and two distinct
    # native draw-sort receipts.
    prior=verify_frames(root)
    for case in CASES:
        receipt=root/case/"native-alpha-pass.txt"
        if receipt.is_symlink() or not receipt.is_file() or (
            receipt.read_bytes()!=expected_receipt(case)
        ):
            raise ValueError(f"Invalid native GPU blend/depth receipt: {case}")
    return {
        "schema":SCHEMA,
        "stage273_independent_frame_audit":prior,
        "guest_native_pass_state_receipts":len(CASES),
        "actual_guest_provenance":"requires real NeXium GitHub Actions workflow",
        "original_ps3_resources":False,
        "physical_switch_verified":False,
        "opaque_rear_depth_write":True,
        "translucent_depth_writes_disabled":True,
    }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",required=True,type=Path)
    parser.add_argument("--report",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        receipt=verify(args.evidence)
        with args.report.open("x",encoding="utf-8") as out:
            json.dump(receipt,out,indent=2,sort_keys=True)
            out.write("\n")
    except (OSError,ValueError,TypeError,KeyError) as error:
        print("Stage274 guest GPU pass evidence rejected: "+str(error),
              file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
