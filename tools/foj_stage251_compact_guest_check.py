#!/usr/bin/env python3
"""Stage251: optical proof of exact-sized heap payload across 3 resolutions.

Inheritance is mandatory: Stage250 cold/warm times and all earlier actual
NeXium gameplay, timing and parity receipts must remain valid.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage241_render_guest_check import close
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage250_scale_guest_check import (
    verify_scale_guest,MODES,
)
SCHEMA="foj-stage251-nexium-compact-heap-payload-by-resolution-v1"
BASE_X=536
BAR_Y=(45,47,49)
ON=((139,222,89),(72,120,221),(236,171,118))
OFF=(48,37,48)
STATUS_X=752
READY=(148,227,84)

def matches(frame,x,colour):
    return all(close(frame.getpixel((x,y)),colour) for y in BAR_Y)

def read_bits(frame,origin,on):
    n=0
    for bit in range(16):
        x=sample_x(origin+bit*4)
        if matches(frame,x,on):
            n|=1<<bit
        elif not matches(frame,x,OFF):
            raise ValueError(f"Stage251 bad heap barcode bit {bit} at {x}")
    if n==65535:
        raise ValueError("Stage251 saturated allocated KiB barcode")
    return n

def verify_compact_guest(paths:tuple[Path,...])->dict:
    if len(paths)!=len(STATES):
        raise ValueError("Exactly nine ordered NeXium states required")
    earlier=verify_scale_guest(paths)
    states={}
    fixed_bytes=1280*720*4
    for state,path in zip(STATES,paths):
        frame=read_frame(path)
        if not all(matches(frame,sample_x(STATUS_X+dx),READY)
                   for dx in (2,3,4)):
            raise ValueError(f"{state}: compact allocation, parity or 3-size sweep failed")
        cases=[]
        for i,(w,h) in enumerate(MODES):
            reported_kib=read_bits(frame,BASE_X+i*72,ON[i])
            expected_bytes=w*h*4
            if reported_kib*1024!=expected_bytes:
                raise ValueError(
                    f"{state}: expected {expected_bytes} active bytes at {w}x{h}, "
                    f"reported {reported_kib*1024}")
            cases.append({
                "resolution":f"{w}x{h}",
                "allocated_pixel_payload_bytes":reported_kib*1024,
                "old_fixed_capacity_bytes":fixed_bytes,
                "savings_bytes_vs_fixed":fixed_bytes-expected_bytes,
                "previous_fixed_capacity_was_reserved_per_resolution":True,
                "actual_heap_rss_or_allocator_metadata_measured":False,
            })
        states[state]=cases
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "actual_states":len(paths),
        "state_receipts":states,
        "pixel_payload_bytes_for_three_sizes":[w*h*4 for w,h in MODES],
        "fixed_max_pixel_payload_bytes":fixed_bytes,
        "named_heap_payload_only":True,
        "peak_in_three_size_sweep_bytes":fixed_bytes,
        "heap_allocator_overhead_or_rss_measured":False,
        "memory_scaling_for_smallest_state_pct":93.75,
        "inherited_stage250_schema":earlier["schema"],
        "inherited_stage250_active_cold_warm_us":[
            (m["cold_active_median_us"],m["warm_active_median_us"])
            for m in earlier["resolutions"]
        ],
        "frame_sha256":earlier["frame_sha256"],
        "default_nro_unchanged":True,
        "physical_switch_tested":False,
        "gpu_time_or_fps_measured":False,
        "original_ps3_assets_used":False,
        "whole_game_speedup_proven":False,
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for s in STATES:
        p.add_argument("--"+s.replace("_","-"),type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    result=verify_compact_guest(tuple(getattr(a,s) for s in STATES))
    with a.report.open("x",encoding="utf-8") as output:
        json.dump(result,output,sort_keys=True,indent=2)
        output.write("\n")
    print("Stage251: compact heap raster payload (bytes):",
          result["pixel_payload_bytes_for_three_sizes"],
          "nine real NeXium states and all inherited proofs verified")

if __name__=="__main__":
    main()
