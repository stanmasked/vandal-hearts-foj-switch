#!/usr/bin/env python3
"""Decode Stage248 real within-process full-frame AB/BA base-cache pairs.

Only CPU software rasterization of generated 8x6 terrain was timed. A guest
parity tile confirms byte-identical private rasters; no GPU or FPS claim.
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
from tools.foj_stage247_base_cache_guest_check import verify_base_cache_guest

SCHEMA="foj-stage248-nexium-inprocess-scene-exact-base-cache-abba-v1"
PAIR_X=(780,852)
BAR_COLOR=((243,188,65),(87,133,234))
BAR_OFF=(48,37,48)
STATUS_X=924
STATUS_READY=(125,232,75)
Y=(13,15,17)
ACTIVE=("selected","hovered","restored","guarded","guard_hovered")
INACTIVE=("initial","hidden","cancelled","ended")

def equal(frame,x,color):
    return all(close(frame.getpixel((x,y)),color) for y in Y)

def read_mean(frame,origin,color):
    result=0
    for bit in range(16):
        x=sample_x(origin+4*bit)
        if equal(frame,x,color):
            result|=1<<bit
        elif not equal(frame,x,BAR_OFF):
            raise ValueError(f"Invalid Stage248 timing sample bit={bit} x={x}")
    if result<=0 or result>=65535:
        raise ValueError("Zero or saturated Stage248 mean")
    return result

def verify_base_pair_guest(paths:tuple[Path,...])->dict:
    if len(paths)!=len(STATES):
        raise ValueError("Exactly nine ordered real NeXium screenshots required")
    earlier=verify_base_cache_guest(paths)
    records={}
    digests={}
    for state,path in zip(STATES,paths):
        image=read_frame(path)
        if not all(equal(image,sample_x(STATUS_X+offset),STATUS_READY)
                   for offset in (2,3,4)):
            raise ValueError(f"{state}: no ready/perfect-parity paired raster proof")
        a=read_mean(image,PAIR_X[0],BAR_COLOR[0])
        b=read_mean(image,PAIR_X[1],BAR_COLOR[1])
        records[state]={
            "cached_mean_us":a,
            "uncached_mean_us":b,
            "uncached_minus_cached_us":b-a,
            "uncached_over_cached_ratio":round(b/a,4),
            "forecast_active":state in ACTIVE,
        }
        digests[state]=hashlib.sha256(path.read_bytes()).hexdigest()
    if len(set(digests.values()))<2:
        raise ValueError("Repeated screenshot cannot verify nine game states")
    delta_active=[records[s]["uncached_minus_cached_us"] for s in ACTIVE]
    delta_inactive=[records[s]["uncached_minus_cached_us"] for s in INACTIVE]
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "guest_processes":1,
        "captured_real_frames":9,
        "pairs_per_window":32,
        "interleaving":"alternating AB/BA, same battle state and software renderer",
        "private_uncached_baseline":True,
        "separately_warmed_forecast_cache_for_each_arm":True,
        "in_guest_private_pixel_parity_verified":True,
        "inherited_stage247_schema":earlier["schema"],
        "states":records,
        "active_median_difference_us":statistics.median(delta_active),
        "inactive_median_difference_us":statistics.median(delta_inactive),
        "active_median_cached_us":statistics.median(
            records[s]["cached_mean_us"] for s in ACTIVE),
        "active_median_uncached_us":statistics.median(
            records[s]["uncached_mean_us"] for s in ACTIVE),
        "frame_sha256":digests,
        "host_performance_inference_valid":False,
        "original_ps3_assets_present":False,
        "physical_switch_tested":False,
        "gpu_or_fps_measured":False,
        "whole_game_speedup_proven":False,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--"+state.replace("_","-"),type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    report=verify_base_pair_guest(tuple(getattr(args,s) for s in STATES))
    with args.report.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,sort_keys=True,indent=2)
        stream.write("\n")
    print("Stage248: within-process paired software raster active cached/uncached medians (us):",
          report["active_median_cached_us"], report["active_median_uncached_us"])

if __name__=="__main__":
    main()
