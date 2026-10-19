#!/usr/bin/env python3
"""Stage250 decode three size-specific cold/warm base raster receipts.

All measurements are generated CPU software-render work within NeXium.
Inherited Stage249 real game state and pixel parity remain mandatory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage241_render_guest_check import close
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage249_stability_guest_check import (
    verify_stability_guest,ACTIVE,INACTIVE,
)
SCHEMA="foj-stage250-nexium-base-raster-three-resolution-scaling-v1"
MODES=((320,180),(640,360),(1280,720))
ON_COLORS=(
    (179,216,85),(83,184,237),
    (237,191,116),(167,139,237),
    (255,172,186),(245,208,104),
)
OFF=(48,37,48)
READY=(148,227,84)
STATUS_X=968
FIRST_X=536
Y=(29,31,33)
FIXED_CAPACITY=1280*720*4

def color_matches(image,x,on):
    return all(close(image.getpixel((x,y)),on) for y in Y)

def number(image,origin,on):
    result=0
    for bit in range(16):
        x=sample_x(origin+4*bit)
        if color_matches(image,x,on):
            result|=1<<bit
        elif not color_matches(image,x,OFF):
            raise ValueError(f"Stage250 invalid color in bit {bit} at x={x}")
    if result<=0 or result>=65535:
        raise ValueError("Zero or saturated Stage250 timing receipt")
    return result

def verify_scale_guest(paths:tuple[Path,...])->dict:
    if len(paths)!=len(STATES):
        raise ValueError("Nine ordered genuine NeXium states required")
    earlier=verify_stability_guest(paths)
    records={}
    sha={}
    for state,path in zip(STATES,paths):
        frame=read_frame(path)
        if not all(color_matches(frame,sample_x(STATUS_X+k),READY)
                   for k in (2,3,4)):
            raise ValueError(f"{state}: missing ready and pixel-parity tile")
        cases=[]
        for i,(width,height) in enumerate(MODES):
            cold=number(frame,FIRST_X+2*i*72,ON_COLORS[2*i])
            warm=number(frame,FIRST_X+(2*i+1)*72,ON_COLORS[2*i+1])
            # Modeled, not a measured full-game speedup: if same scene
            # persisted for 32 base draws instead of being invalidated.
            uncached_32=32*cold
            cached_32=cold+31*warm
            cases.append({
                "width":width,"height":height,"rgba32_active_bytes":width*height*4,
                "base_cold_us":cold,"base_warm_us":warm,
                "cold_minus_warm_us":cold-warm,
                "hypothetical_32_repeat_savings_us":uncached_32-cached_32,
                "hypothetical_32_repeat_speed_ratio":round(
                    uncached_32/cached_32,4),
                "cold_equals_base_recompute_not_gameplay_latency":True,
            })
        records[state]=cases
        sha[state]=hashlib.sha256(path.read_bytes()).hexdigest()
    if len(set(sha.values()))<2:
        raise ValueError("Reused PNG cannot substantiate nine real states")
    medians=[]
    for i,(width,height) in enumerate(MODES):
        medians.append({
            "width":width,"height":height,
            "rgba32_active_bytes":width*height*4,
            "cold_active_median_us":statistics.median(
                records[s][i]["base_cold_us"] for s in ACTIVE),
            "warm_active_median_us":statistics.median(
                records[s][i]["base_warm_us"] for s in ACTIVE),
            "cold_inactive_median_us":statistics.median(
                records[s][i]["base_cold_us"] for s in INACTIVE),
            "warm_inactive_median_us":statistics.median(
                records[s][i]["base_warm_us"] for s in INACTIVE),
        })
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "guest_processes":1,
        "actual_game_states":len(paths),
        "resolutions":medians,
        "states":records,
        "private_static_cache_capacity_bytes":FIXED_CAPACITY,
        "private_cache_always_reserves_max_resolution_even_for_small_cases":True,
        "measured_total_experimental_memory_bytes":None,
        "named_experimental_allocations_under_bytes":21*1024*1024,
        "scene_change_invalidates_cache_every_resolution":True,
        "independent_uncached_reference_pixels_checked_in_guest":True,
        "inherited_stage249_schema":earlier["schema"],
        "frame_sha256":sha,
        "break_even_calculation_model_only":True,
        "physical_switch_tested":False,
        "gpu_time_or_fps_measured":False,
        "original_ps3_assets_used":False,
        "whole_game_speedup_proven":False,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--"+state.replace("_","-"),type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    result=verify_scale_guest(tuple(getattr(args,s) for s in STATES))
    with args.report.open("x",encoding="utf-8") as file:
        json.dump(result,file,sort_keys=True,indent=2)
        file.write("\n")
    print("Stage250: 320x180, 640x360, 1280x720 CPU cold/warm (us):",
          [(r["width"],r["cold_active_median_us"],r["warm_active_median_us"])
           for r in result["resolutions"]])

if __name__=="__main__":
    main()
