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
    # Separate third NeXium guest with exactly one generated alpha texel
    # changed. No PNG should be accepted as proof of this early rejection.
    negative=root/"rear-alpha-negative"
    negative_input=negative/"generated-input.json"
    negative_marker=negative/"native-rear-alpha-reject.txt"
    negative_log=negative/"guest.log"
    if any(path.is_symlink() or not path.is_file() for path in
           (negative_input,negative_marker,negative_log)):
        raise ValueError("Missing Stage274 real negative guest evidence")
    negative_info=json.loads(negative_input.read_text(encoding="utf-8"))
    if (negative_info.get("schema")!=
            "foj.stage274.native_rear_alpha_negative.v1" or
        negative_info.get("scenario")!="one-rear-alpha-254" or
        negative_info.get("generated_only") is not True or
        negative_info.get("original_ps3_resources") is not False or
        negative_info.get("guest_verified") is not False or
        negative_info.get("changed_file")!="material2.dds" or
        negative_info.get("changed_bytes")!=1 or
        negative_info.get("original_alpha")!=255 or
        negative_info.get("mutated_alpha")!=254 or
        negative_info.get("expected_native_rejection_marker")!=
            "FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1" or
        negative_marker.read_bytes()!=
            b"FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1\\n"):
        raise ValueError("Incorrect Stage274 native rear DDS refusal evidence")
    return {
        "schema":SCHEMA,
        "stage273_independent_frame_audit":prior,
        "negative_generated_rear_dds_refused_before_gpu":True,
        "native_rear_alpha_rejection_receipts":1,
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
