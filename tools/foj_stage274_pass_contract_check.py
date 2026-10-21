#!/usr/bin/env python3
"""Stage274 independent final evidence audit for deko3d GPU state.

Only a real separate NeXium guest invoked by GitHub Actions establishes
the guest-origin of receipts or pixels; synthetic host tests do not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from tools.foj_stage273_dynamic_gpu_check import verify as verify_frames
from tools.foj_stage273_dynamic_gpu_sd import CASES, BACK_TO_FRONT
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import COOL

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
        # A positive GPU-rendering guest must not ALSO claim its decoded
        # opaque rear DDS failed the earlier Stage274 pre-GPU check.
        positive=root/case
        contradiction=positive/"native-rear-alpha-reject.txt"
        if contradiction.exists() or contradiction.is_symlink():
            raise ValueError(
                f"Contradictory positive/rear-alpha guest evidence: {case}")
        receipt=positive/"native-alpha-pass.txt"
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
    # The single-byte rear-DDS failure happens before both success-marker
    # creation and GPU boot. Refuse contradictory artifacts even if the
    # expected negative witness itself is correct.
    for forbidden in (
            "native-sort-pass.txt","native-alpha-pass.txt",
            "gpu-initial.png","gpu-later.png"):
        extra=negative/forbidden
        if extra.exists() or extra.is_symlink():
            raise ValueError(
                "Contradictory negative GPU guest evidence: "+forbidden)
    if any(negative.glob("foj-boot-*.txt")):
        raise ValueError("Contradictory negative GPU boot evidence")
    negative_info=json.loads(negative_input.read_text(encoding="utf-8"))
    # Recompute both identities from the PUBLIC synthetic DDS formula.
    # A self-reported changed_bytes=1 is not sufficient to establish which
    # texture image actually went into the negative guest root.
    canonical_dds=generated_dds((*COOL,255))
    expected_bad_dds=bytearray(canonical_dds)
    if len(expected_bad_dds)!=128+64*64*4 or expected_bad_dds[131]!=255:
        raise ValueError("Stage274 synthetic rear DDS contract changed")
    expected_bad_dds[131]=254
    clean_sha256=hashlib.sha256(canonical_dds).hexdigest()
    bad_sha256=hashlib.sha256(expected_bad_dds).hexdigest()
    # Host-measured actual source DDS on both sides of the real guest is
    # part of the archived evidence, not merely two hashes reported by
    # the generator. Reject absent, symlinked, or doctored observations.
    for phase in ("before","after"):
        observation=negative/f"rear-dds-{phase}.json"
        if observation.is_symlink() or not observation.is_file():
            raise ValueError(f"Missing Stage274 {phase} DDS observation")
        details=json.loads(observation.read_text(encoding="utf-8"))
        expected_observation={
            "schema":"foj.stage274.synthetic_rear_dds_observation.v1",
            "phase":phase,
            "source":"generated-only material2.dds",
            "ddsdigest_sha256":bad_sha256,
            "dds_length_bytes":len(expected_bad_dds),
            "original_ddsdigest_sha256":clean_sha256,
            "modified_alpha_offset":131,
            "modified_alpha_value":254,
            "original_ps3_resources":False,
            "guest_gpu_success_claimed":False,
        }
        if details!=expected_observation:
            raise ValueError(
                f"Invalid Stage274 {phase} real-guest input DDS observation")
    if (negative_info.get("original_rear_dds_sha256")!=clean_sha256 or
        negative_info.get("mutated_rear_dds_sha256")!=bad_sha256):
        raise ValueError("Stage274 negative DDS SHA-256 provenance mismatch")
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
            b"FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1\n"):
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
