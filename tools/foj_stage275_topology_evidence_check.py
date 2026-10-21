#!/usr/bin/env python3
"""Stage275 evidence: one valid real GPU scene and two genuine early rejects.

Only the CI NeXium process establishes actual native execution. A manually
constructed directory can test this classifier but is not runtime proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image,ImageChops
from tools.foj_stage271_generated_negative_sd import rejected_actor
from tools.foj_stage273_dynamic_gpu_sd import (
    BACK_TO_FRONT,expected_rgb,generated_actor,
)
from tools.foj_stage273_dynamic_gpu_check import inspect
from tools.foj_stage267_gpu_three_layer_check import BACKGROUNDS
from tools.foj_stage274_pass_contract_check import expected_receipt
from tools.foj_stage275_negative_topology_sd import CASES,SCHEMA,MESSAGE


def required_file(path:Path)->bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Stage275 missing or linked artifact: {path.name}")
    return path.read_bytes()


def verify(root:Path)->dict:
    root=Path(root)
    positive=root/"original"
    scene=json.loads(required_file(positive/"generated-input.json"))
    if (scene.get("schema")!="foj.stage273.dynamic_gpu_sort.v1" or
        scene.get("scenario")!="original" or
        scene.get("generated_only") is not True or
        scene.get("guest_proof_claimed") is not False or
        scene.get("expected_native_pass_order")!=list(BACK_TO_FRONT["original"]) or
        scene.get("expected_overlap_rgb")!=list(expected_rgb("original"))):
        raise ValueError("Stage275 untrusted valid positive scene manifest")
    if required_file(positive/"native-sort-pass.txt")!=(
            b"FOJ_NATIVE_SORT_V1 2,1,0\n") or (
            required_file(positive/"native-alpha-pass.txt")!=
            expected_receipt("original")):
        raise ValueError("Stage275 positive guest GPU state or sort changed")
    for forbidden in ("native-topology-reject.txt","native-rear-alpha-reject.txt"):
        marker=positive/forbidden
        if marker.exists() or marker.is_symlink():
            raise ValueError("Stage275 contradictory positive GPU state")
    first=positive/"gpu-initial.png"
    later=positive/"gpu-later.png"
    inspected1=inspect(first,"original")
    inspected2=inspect(later,"original")
    with Image.open(first) as fi, Image.open(later) as la:
        a,b=fi.convert("RGB"),la.convert("RGB")
    if ImageChops.difference(a,b).getbbox() is None:
        raise ValueError("Stage275 identical positive GPU frames")
    if sum(a.getpixel(q)!=b.getpixel(q) for q in BACKGROUNDS)<3:
        raise ValueError("Stage275 positive GPU clear-color did not change")
    if [inspected1[k]["matching_pixels"] for k in inspected1]!=[
            inspected2[k]["matching_pixels"] for k in inspected2]:
        raise ValueError("Stage275 positive material coverage changed")

    seen=[]
    for case in CASES:
        folder=root/case
        manifest=json.loads(required_file(folder/"generated-input.json"))
        wanted=rejected_actor(case)
        if (manifest.get("schema")!=SCHEMA or
            manifest.get("topology_case")!=case or
            manifest.get("generated_only") is not True or
            manifest.get("original_ps3_resources") is not False or
            manifest.get("native_gpu_boot_claimed") is not False or
            manifest.get("guest_proof_claimed") is not False or
            manifest.get("changed_file")!="actor.fojrm" or
            manifest.get("untouched_rear_dds") is not True or
            manifest.get("expected_native_marker")!=MESSAGE or
            manifest.get("actor_sha256")!=hashlib.sha256(wanted).hexdigest() or
            manifest.get("safe_original_actor_sha256")!=hashlib.sha256(
                generated_actor("original")).hexdigest()):
            raise ValueError(f"Stage275 invalid generated unsafe actor: {case}")
        digest=hashlib.sha256(wanted).hexdigest().encode("ascii")+b"\n"
        for phase in ("before","after"):
            if required_file(folder/f"actor-{phase}.sha256")!=digest:
                raise ValueError(f"Stage275 altered actor witness: {case}/{phase}")
        if required_file(folder/"native-topology-reject.txt")!=(
                MESSAGE+"\n").encode("ascii"):
            raise ValueError(f"Stage275 missing native unsafe rejection: {case}")
        required_file(folder/"guest.log")
        for forbidden in ("native-sort-pass.txt","native-alpha-pass.txt",
                          "native-rear-alpha-reject.txt","gpu-initial.png",
                          "gpu-later.png"):
            unexpected=folder/forbidden
            if unexpected.exists() or unexpected.is_symlink():
                raise ValueError(f"Stage275 contradictory unsafe guest: {case}")
        if any(folder.glob("foj-boot-*.txt")):
            raise ValueError(f"Stage275 illegal GPU boot after unsafe geometry: {case}")
        seen.append(case)
    return {
        "schema":"foj.stage275.real_native_topology_rejection.v1",
        "native_unsafe_refusals":seen,
        "positive_guest_frames":2,
        "positive_native_sort_and_gpu_state":True,
        "generated_only":True,
        "original_ps3_resources":False,
        "physical_switch_verified":False,
        "actual_guest_provenance":"requires completed real NeXium CI workflow",
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        result=verify(args.evidence)
        with args.report.open("x",encoding="utf-8") as out:
            json.dump(result,out,sort_keys=True,indent=2)
            out.write("\n")
    except (OSError,ValueError,TypeError,KeyError) as error:
        print("Stage275 native topology evidence rejected: "+str(error),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
