#!/usr/bin/env python3
"""Audit three actual NeXium rejection receipts gathered by a separate runner.

This verifier cannot itself authenticate that the files came from NeXium;
only the GitHub Actions guest drive (fresh roots + real NRO execution)
provides that provenance. Host-made fixtures test the classifier only.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from tools.foj_stage271_generated_negative_sd import CASES

SCHEMA="foj.stage271.native_guest_rejection.v1"
RECEIPT=b"FOJ_NATIVE_UNSAFE_REJECT_V1 exit=8 pre_gpu=1\n"


def verify(root: Path, positive_control: Path | None = None) -> dict:
    items={}
    for case in CASES:
        folder=root/case
        expected=(folder/"native-reject.txt")
        if expected.is_symlink() or not expected.is_file() or expected.read_bytes()!=RECEIPT:
            raise ValueError(f"Missing or wrong guest-generated receipt: {case}")
        info_path=folder/"generated-input.json"
        if info_path.is_symlink() or not info_path.is_file():
            raise ValueError(f"Missing synthetic input provenance: {case}")
        info=json.loads(info_path.read_text(encoding="utf-8"))
        if info.get("schema")!="foj.stage271.negative_generated_actor.v1" or (
            info.get("negative_case")!=case or
            info.get("generated_only") is not True or
            info.get("expected_native_exit_code")!=8 or
            info.get("guest_execution_verified") is not False
        ):
            raise ValueError(f"Incorrect generated fixture receipt: {case}")
        if not (folder/"guest.log").is_file():
            raise ValueError(f"Missing guest process log: {case}")
        items[case]={
            "guest_marker":"FOJ_NATIVE_UNSAFE_REJECT_V1",
            "declared_native_exit":8,
            "pre_gpu":True,
            "fixture_source":"generated_only",
        }
    control_receipt=None
    if positive_control is not None:
        control=Path(positive_control)
        info_path=control/"generated-input.json"
        if info_path.is_symlink() or not info_path.is_file():
            raise ValueError("No authentic generated safe control input receipt")
        info=json.loads(info_path.read_text(encoding="utf-8"))
        if (info.get("case")!="both-half" or
            info.get("stage269_geometry_guard")!="safe_fixed_back_to_front" or
            info.get("stage269_checked_order")!=["cool","warm","violet"] or
            info.get("generated_only") is not True):
            raise ValueError("Safe-control scene was not preflight accepted")
        if not (control/"guest.log").is_file():
            raise ValueError("Missing safe-control guest log")
        from PIL import Image
        from tools.foj_stage267_gpu_three_layer_check import inspect, BACKGROUNDS
        before=control/"gpu-initial.png"
        after=control/"gpu-later.png"
        probes_a=inspect(before,"both-half")
        probes_b=inspect(after,"both-half")
        with Image.open(before) as im_a, Image.open(after) as im_b:
            a=im_a.convert("RGB")
            b=im_b.convert("RGB")
        if sum(a.getpixel(p)!=b.getpixel(p) for p in BACKGROUNDS)<3:
            raise ValueError("No distinct framebuffer phase in positive-control guest")
        # The NRO rejection marker absence is independently required by
        # the NeXium workflow checking the fresh SD root after guest exit.
        control_receipt={
            "scenario":"both-half",
            "same_diagnostic_nro":True,
            "expected_rgb":[111,100,162],
            "first_frame_probes":probes_a,
            "second_frame_probes":probes_b,
            "gpu_clear_phase_changed":True,
            "no_rejection_marker_verified_by_guest_driver":True,
        }
    return {
        "schema":SCHEMA,
        "positive_control":control_receipt,
        "cases":items,
        "native_receipts_checked":len(items),
        "emulator_run_provenance":"github_actions_separate_guest_process",
        "host_unit_fixtures_are_not_emulator_proof":True,
        "actual_host_process_exit_code_measured":False,
        "actual_original_ps3_assets_used":False,
        "physical_switch_verified":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--positive-control",type=Path)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        result=verify(args.evidence,args.positive_control)
        with args.report.open("x",encoding="utf-8") as file:
            json.dump(result,file,indent=2,sort_keys=True)
            file.write("\n")
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("Stage271 guest evidence rejected: "+str(exc),file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
