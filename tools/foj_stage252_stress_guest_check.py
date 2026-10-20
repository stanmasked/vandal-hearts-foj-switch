#!/usr/bin/env python3
"""Stage252 optical evidence: 96 cold/warm cycles and 8 injected failures.

Every Stage251, Stage250 and older actual NeXium frame proof is required.
This is synthetic CPU raster and allocation instrumentation, not game FPS.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage241_render_guest_check import close
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage251_compact_guest_check import verify_compact_guest
SCHEMA="foj-stage252-compact-cache-injected-fault-96-cycle-endurance-v1"
ORIGIN=536
STEP=72
Y=(61,63,65)
COLORS=((141,218,92),(108,159,213),(234,205,108),(239,113,185))
OFF=(48,37,48)
STATUS_X=824
READY=(148,227,84)
EXPECTED=(96,8,96,3600)

def matches(im,x,colour):
    return all(close(im.getpixel((x,y)),colour) for y in Y)

def read_bits(im,origin,on):
    result=0
    for bit in range(16):
        x=sample_x(origin+bit*4)
        if matches(im,x,on):
            result|=1<<bit
        elif not matches(im,x,OFF):
            raise ValueError(f"Stage252 corrupt endurance barcode x={x}")
    if result==65535:
        raise ValueError("Stage252 saturated optical value")
    return result

def verify_stress_guest(paths:tuple[Path,...])->dict:
    if len(paths)!=len(STATES):
        raise ValueError("Exactly 9 real states required")
    inherited=verify_compact_guest(paths)
    records={}
    for state,path in zip(STATES,paths):
        frame=read_frame(path)
        if not all(matches(frame,sample_x(STATUS_X+dx),READY)
                   for dx in (2,3,4)):
            raise ValueError(f"{state}: endurance parity or fail-closed status")
        vals=tuple(read_bits(frame,ORIGIN+STEP*i,COLORS[i])
                   for i in range(4))
        if vals!=EXPECTED:
            raise ValueError(
                f"{state}: expected {EXPECTED}, observed {vals}")
        records[state]={
            "cycles":vals[0],
            "injected_malloc_failures":vals[1],
            "successful_allocations":vals[2],
            "maximum_requested_pixel_kib":vals[3],
            "cache_releases_verified_in_guest":True,
            "cold_warm_independent_parity_verified_in_guest":True,
            "all_injected_failures_recovered":True
        }
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "genuine_battle_states":len(paths),
        "stress_receipt":records,
        "guest_execution_count":1,
        "stress_run_before_visible_gameplay":True,
        "cycles_executed_once_not_per_frame":EXPECTED[0],
        "simulated_allocation_failures":EXPECTED[1],
        "successful_allocations":EXPECTED[2],
        "matched_releases":EXPECTED[2],
        "max_pixel_payload_kib":EXPECTED[3],
        "heap_rss_measured":False,
        "end_to_end_fps_measured":False,
        "physical_switch_tested":False,
        "ps3_original_engine_assets_used":False,
        "inherited_stage251_schema":inherited["schema"],
        "inherited_stage250_active_cold_warm_us":
            inherited["inherited_stage250_active_cold_warm_us"],
        "frame_sha256":inherited["frame_sha256"],
        "whole_game_improvement_proven":False,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--"+state.replace("_","-"),type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    data=verify_stress_guest(tuple(getattr(args,s) for s in STATES))
    with args.report.open("x",encoding="utf-8") as output:
        json.dump(data,output,indent=2,sort_keys=True)
        output.write("\n")
    print("Stage252 NeXium endurance: 96 cycles; 8 simulated malloc "
          "failures; 96 allocations, 96 releases; 3600 KiB peak payload; "
          "9 real gameplay screenshots and Stage251 ancestors accepted")

if __name__=="__main__":
    main()
