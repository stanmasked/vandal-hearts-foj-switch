#!/usr/bin/env python3
"""Stage254 NeXium receipt: exact-size against bounded 900-KiB floor.

Nine actual screenshots are mandatory; Stage253 and older optical proofs
must also pass before decoding the new six-value comparison receipt.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage241_render_guest_check import close
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage253_churn_guest_check import verify_churn_guest

SCHEMA="foj-stage254-900kib-reuse-compare-v1"
ORIGIN=536
STEP=72
STATUS_X=968
# Guest y92..99 appears near y89..96 in actual 1280x720 NeXium capture.
Y=(90,92,94)
ON=((163,214,119),(117,196,229),(231,201,106),
    (229,146,175),(174,148,218),(237,192,156))
OFF=(48,37,48)
READY=(148,227,84)
EXPECTED=(384,48,32,32,16,675)

def matches(image,x,color):
    return all(close(image.getpixel((x,y)),color) for y in Y)

def word(image,origin,on):
    value=0
    for bit in range(16):
        x=sample_x(origin+4*bit)
        if matches(image,x,on):
            value|=1<<bit
        elif not matches(image,x,OFF):
            raise ValueError(f"Stage254 corrupt optical bit {bit} at x={x}")
    if value==65535:
        raise ValueError("Stage254 saturated optical counter")
    return value

def verify_reuse_guest(paths:tuple[Path,...])->dict:
    if len(paths)!=len(STATES):
        raise ValueError("Exactly nine actual NeXium states required")
    parent=verify_churn_guest(paths)
    receipts={}
    for state,path in zip(STATES,paths):
        image=read_frame(path)
        if not all(matches(image,sample_x(STATUS_X+i),READY)
                   for i in (2,3,4)):
            raise ValueError(f"{state}: Stage254 comparator not ready")
        vals=tuple(word(image,ORIGIN+STEP*i,ON[i]) for i in range(6))
        if vals!=EXPECTED:
            raise ValueError(f"{state}: expected {EXPECTED}, observed {vals}")
        receipts[state]=dict(zip(("frames","exact_allocations",
            "reuse_allocations","reuse_releases","allocations_saved",
            "additional_low_resolution_kib"),vals))
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "actual_battle_states":len(paths),
        "test_frames":384,
        "exact_policy_allocations":48,
        "bounded_reuse_allocations":32,
        "bounded_reuse_releases":32,
        "allocations_avoided":16,
        "additional_capacity_at_320x180_kib":675,
        "peak_allocated_pixel_payload_kib":3600,
        "pixel_reference_checked_in_guest":True,
        "whole_game_fps_measured":False,
        "allocator_fragmentation_or_rss_measured":False,
        "physical_nintendo_switch_tested":False,
        "original_ps3_content_used":False,
        "inherit_stage253_schema":parent["schema"],
        "frames_sha256":parent["frame_sha256"],
        "states":receipts,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        p.add_argument("--"+state.replace("_","-"),required=True,type=Path)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    result=verify_reuse_guest(tuple(getattr(a,s) for s in STATES))
    with a.report.open("x",encoding="utf-8") as file:
        json.dump(result,file,sort_keys=True,indent=2)
        file.write("\n")
    print("Stage254 NeXium: 384 frames, 48 exact versus 32 bounded "
          "allocations (16 avoided), 32 releases, +675 KiB at 320x180, "
          "3600 KiB peak; nine screenshots plus Stage253 inheritance passed")

if __name__=="__main__":main()
