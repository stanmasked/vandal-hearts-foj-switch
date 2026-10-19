#!/usr/bin/env python3
"""Stage249: strict optical proof of base-refill cost and three AB/BA windows.

Real NeXium guest only; barcodes measure CPU raster, not GPU/display/FPS.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage248_base_pair_guest_check import (
    equal, verify_base_pair_guest,
)
SCHEMA="foj-stage249-nexium-inprocess-base-refill-repeatability-v1"
COLD_X=536
WARM_X=608
SPREAD_X=680
STATUS_X=752
ON_COLORS=((170,211,60),(170,124,209),(245,140,58))
OFF=(48,37,48)
READY=(148,227,84)
ACTIVE=("selected","hovered","restored","guarded","guard_hovered")
INACTIVE=("initial","hidden","cancelled","ended")

def read_bar(frame,origin:int,on:tuple[int,int,int], *,allow_zero:bool):
    value=0
    for bit in range(16):
        x=sample_x(origin+bit*4)
        if equal(frame,x,on):
            value|=1<<bit
        elif not equal(frame,x,OFF):
            raise ValueError(f"Stage249 invalid bit {bit} at x={x}")
    if value==65535 or (value==0 and not allow_zero):
        raise ValueError("Stage249 zero or saturated microsecond barcode")
    return value

def verify_stability_guest(paths:tuple[Path,...])->dict:
    if len(paths)!=len(STATES):
        raise ValueError("Exactly nine ordered real guest PNGs required")
    earlier=verify_base_pair_guest(paths)
    states={}
    digests={}
    for state,path in zip(STATES,paths):
        image=read_frame(path)
        if not all(equal(image,sample_x(STATUS_X+offset),READY)
                   for offset in (2,3,4)):
            raise ValueError(f"{state}: fewer than three valid AB/BA windows or parity failure")
        cold=read_bar(image,COLD_X,ON_COLORS[0],allow_zero=False)
        warm=read_bar(image,WARM_X,ON_COLORS[1],allow_zero=False)
        spread=read_bar(image,SPREAD_X,ON_COLORS[2],allow_zero=True)
        states[state]={
            "base_cold_refill_us":cold,
            "base_warm_copy_us":warm,
            "cold_minus_warm_us":cold-warm,
            "largest_32_pair_window_spread_us":spread,
            "paired_window_count_at_least":3,
            "latest_cached_full_frame_us":earlier["states"][state]["cached_mean_us"],
            "latest_uncached_full_frame_us":earlier["states"][state]["uncached_mean_us"],
            "forecast_active":state in ACTIVE,
        }
        digests[state]=hashlib.sha256(path.read_bytes()).hexdigest()
    if len(set(digests.values()))<2:
        raise ValueError("Replayed identical PNGs cannot prove battle states")
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "guest_processes":1,
        "real_game_state_screenshots":len(paths),
        "complete_paired_windows_per_scene_at_least":3,
        "pairs_per_window":32,
        "scene_invalidation_restart_enforced_in_guest":True,
        "inherited_stage248_schema":earlier["schema"],
        "states":states,
        "active_median_base_cold_refill_us":statistics.median(
            states[s]["base_cold_refill_us"] for s in ACTIVE),
        "active_median_base_warm_copy_us":statistics.median(
            states[s]["base_warm_copy_us"] for s in ACTIVE),
        "active_median_worst_window_spread_us":statistics.median(
            states[s]["largest_32_pair_window_spread_us"] for s in ACTIVE),
        "inactive_median_worst_window_spread_us":statistics.median(
            states[s]["largest_32_pair_window_spread_us"] for s in INACTIVE),
        "frame_sha256":digests,
        "original_ps3_assets_used":False,
        "physical_switch_tested":False,
        "gpu_time_or_fps_measured":False,
        "whole_game_speedup_proven":False,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--"+state.replace("_","-"),type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    result=verify_stability_guest(tuple(getattr(args,s) for s in STATES))
    with args.report.open("x",encoding="utf-8") as output:
        json.dump(result,output,indent=2,sort_keys=True)
        output.write("\n")
    print("Stage249: active cold/warm synthetic base raster medians (us):",
          result["active_median_base_cold_refill_us"],
          result["active_median_base_warm_copy_us"],
          "median worst paired-window spread (us):",
          result["active_median_worst_window_spread_us"])

if __name__=="__main__":
    main()
