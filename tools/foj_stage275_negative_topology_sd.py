#!/usr/bin/env python3
"""Stage275 unsafe dynamic GPU guest, from invented geometry ONLY.

Build one fresh NeXium SD root with all Stage273/274-generated shaders,
DDS materials, and one deliberately unsafe *three-triangle actor*.
The legitimate dynamic C11 sorter must refuse before GPU initialization.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from tools.foj_stage271_generated_negative_sd import rejected_actor
from tools.foj_stage273_dynamic_gpu_sd import install_dynamic,generated_actor
from tools.foj_stage267_generated_multiblend_sd import SUBDIR
from tools.foj_stage268_transparency_crossing import UnsafeTransparencyOrder
from tools.foj_stage273_dynamic_gpu_sd import safe_draw_order

CASES=("crossing","coplanar")
SCHEMA="foj.stage275.native_unsafe_dynamic_topology.v1"
MESSAGE="FOJ_NATIVE_TOPOLOGY_REJECT_V1 pre_gpu=1 unsafe=1"


def install_negative(root:Path,shaders:Path,case:str)->dict:
    if case not in CASES:
        raise ValueError("Unsupported Stage275 unsafe topology case")
    canonical=generated_actor("original")
    bad=rejected_actor(case)
    if len(bad)!=len(canonical) or bad==canonical:
        raise ValueError("Invalid generated-only unsafe actor shape")
    try:
        safe_draw_order(bad)
    except UnsafeTransparencyOrder:
        pass
    else:
        raise ValueError("Generated actor unexpectedly sortable")
    report=install_dynamic(root,shaders,"original")
    actor=Path(root)/SUBDIR/"actor.fojrm"
    if actor.is_symlink() or not actor.is_file() or actor.read_bytes()!=canonical:
        raise ValueError("Stage275 original actor unexpectedly changed")
    actor.write_bytes(bad)
    if actor.read_bytes()!=bad:
        raise ValueError("Stage275 synthetic unsafe geometry write failed")
    # Marker is NEVER prepared by the host. It must be written by actual
    # native NRO, using exclusive create, after an unsafe C11 sort result.
    if any((actor.parent/name).exists() or (actor.parent/name).is_symlink()
           for name in ("foj-native-topology-reject.txt",
                        "foj-native-sort-pass.txt",
                        "foj-native-alpha-pass.txt",
                        "foj-native-rear-alpha-reject.txt")):
        raise ValueError("Generated root unexpectedly contains native witness")
    report.update({
        "schema":SCHEMA,
        "topology_case":case,
        "generated_only":True,
        "original_ps3_resources":False,
        "native_gpu_boot_claimed":False,
        "guest_proof_claimed":False,
        "actor_sha256":hashlib.sha256(bad).hexdigest(),
        "safe_original_actor_sha256":hashlib.sha256(canonical).hexdigest(),
        "expected_native_marker":MESSAGE,
        "changed_file":"actor.fojrm",
        "untouched_rear_dds":True,
    })
    return report


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-root",type=Path,required=True)
    p.add_argument("--shaders",type=Path,required=True)
    p.add_argument("--case",choices=CASES,required=True)
    args=p.parse_args(argv)
    try:
        print(json.dumps(install_negative(
            args.data_root,args.shaders,args.case),sort_keys=True))
    except (OSError,ValueError) as error:
        print("Stage275 unsafe generated actor rejected: "+str(error),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
