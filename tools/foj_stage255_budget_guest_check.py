#!/usr/bin/env python3
"""Stage255 opt-in tight-budget optical proof from nine actual NeXium images.

The Stage254 proof and all inherited prior image checks must pass first.
This is not evidence of physical Switch FPS, RAM, or native PS3 assets.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage241_render_guest_check import close
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage254_reuse_guest_check import verify_reuse_guest,ON,OFF,READY

SCHEMA="foj-stage255-exact-budget-fallback-v1"
ORIGIN=536
STEP=72
STATUS_X=968
# Guest y108..115 maps to y105..112 in 1280x720 NeXium screenshots.
Y=(106,108,110)
EXPECTED=(384,48,48,192,192,16)

def matches(image,x,color):
    return all(close(image.getpixel((x,y)),color) for y in Y)

def word(image,origin,on):
    value=0
    for bit in range(16):
        x=sample_x(origin+4*bit)
        if matches(image,x,on):
            value |= 1<<bit
        elif not matches(image,x,OFF):
            raise ValueError(f"Stage255 corrupt optical bit {bit} at x={x}")
    if value==65535:
        raise ValueError("Stage255 saturated optical counter")
    return value

def verify_budget_guest(paths:tuple[Path,...])->dict:
    if len(paths)!=len(STATES):
        raise ValueError("Exactly nine actual NeXium states required")
    inherited=verify_reuse_guest(paths)
    receipts={}
    for state,path in zip(STATES,paths):
        image=read_frame(path)
        if not all(matches(image,sample_x(STATUS_X+i),READY)
                   for i in (2,3,4)):
            raise ValueError(f"{state}: Stage255 comparator not ready")
        observed=tuple(word(image,ORIGIN+STEP*i,ON[i]) for i in range(6))
        if observed!=EXPECTED:
            raise ValueError(f"{state}: expected {EXPECTED}, observed {observed}")
        receipts[state]=dict(zip(("frames","allocations","releases",
            "hits","misses","low_resolution_fallback_blocks"),observed))
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "actual_battle_states":len(paths),
        "test_frames":384,
        "tight_budget_allocations":48,
        "tight_budget_releases":48,
        "tight_budget_hits":192,
        "tight_budget_misses":192,
        "low_resolution_fallback_blocks":16,
        "low_resolution_exact_capacity_kib":225,
        "stage254_unchanged_allocations":inherited["bounded_reuse_allocations"],
        "original_ps3_content_used":False,
        "whole_game_fps_measured":False,
        "physical_nintendo_switch_tested":False,
        "allocator_fragmentation_or_rss_measured":False,
        "pixel_reference_checked_in_guest":True,
        "inherited_stage254_schema":inherited["schema"],
        "frames_sha256":inherited["frames_sha256"],
        "states":receipts,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        p.add_argument("--"+state.replace("_","-"),required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    a=p.parse_args()
    result=verify_budget_guest(tuple(getattr(a,s) for s in STATES))
    with a.report.open("x",encoding="utf-8") as file:
        json.dump(result,file,sort_keys=True,indent=2)
        file.write("\n")
    print("Stage255 NeXium: 384 frames, 48 allocations and releases, "
          "192 hits/misses, 16 exact-size low-res fallback blocks; "
          "nine states and inherited Stage254 optical evidence verified.")

if __name__=="__main__":main()
