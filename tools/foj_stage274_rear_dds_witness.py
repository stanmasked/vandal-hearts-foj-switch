#!/usr/bin/env python3
"""Stage274 exact generated-only DDS witness before/after the real guest.

This measures a local test input, not GPU output nor private PS3 contents.
Two byte-exact measurements are required around the NeXium guest; each
receipt is created exclusively, never overwriting older evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import COOL

SCHEMA="foj.stage274.synthetic_rear_dds_observation.v1"
PHASES=("before","after")


def expected_images()->tuple[bytes,bytes]:
    pristine=generated_dds((*COOL,255))
    if len(pristine)!=128+64*64*4 or pristine[131]!=255:
        raise ValueError("Generated rear DDS contract unexpectedly changed")
    mutated=bytearray(pristine)
    mutated[131]=254
    return pristine,bytes(mutated)


def observe(dds:Path,manifest:Path,phase:str)->dict:
    if phase not in PHASES:
        raise ValueError("Invalid Stage274 DDS observation phase")
    dds,manifest=Path(dds),Path(manifest)
    if (dds.is_symlink() or manifest.is_symlink() or
        not dds.is_file() or not manifest.is_file()):
        raise ValueError("Unsafe or absent Stage274 DDS/manifest input")
    original,mutated=expected_images()
    source=json.loads(manifest.read_text(encoding="utf-8"))
    expected_clean=hashlib.sha256(original).hexdigest()
    expected_mutated=hashlib.sha256(mutated).hexdigest()
    if (source.get("schema")!="foj.stage274.native_rear_alpha_negative.v1"
        or source.get("scenario")!="one-rear-alpha-254"
        or source.get("changed_bytes")!=1
        or source.get("original_alpha")!=255
        or source.get("mutated_alpha")!=254
        or source.get("generated_only") is not True
        or source.get("original_ps3_resources") is not False
        or source.get("original_rear_dds_sha256")!=expected_clean
        or source.get("mutated_rear_dds_sha256")!=expected_mutated):
        raise ValueError("Invalid Stage274 generated-only DDS provenance")
    actual=dds.read_bytes()
    if actual!=mutated:
        raise ValueError("Stage274 guest DDS changed from exact one-byte fixture")
    return {
        "schema":SCHEMA,
        "phase":phase,
        "source":"generated-only material2.dds",
        "ddsdigest_sha256":hashlib.sha256(actual).hexdigest(),
        "dds_length_bytes":len(actual),
        "original_ddsdigest_sha256":expected_clean,
        "modified_alpha_offset":131,
        "modified_alpha_value":254,
        "original_ps3_resources":False,
        "guest_gpu_success_claimed":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dds",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--phase",required=True,choices=PHASES)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args(argv)
    try:
        result=observe(args.dds,args.manifest,args.phase)
        with args.output.open("x",encoding="utf-8") as destination:
            json.dump(result,destination,indent=2,sort_keys=True)
            destination.write("\n")
    except (OSError,ValueError,TypeError,KeyError) as error:
        print("Stage274 rear-DDS witness failed: "+str(error),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
