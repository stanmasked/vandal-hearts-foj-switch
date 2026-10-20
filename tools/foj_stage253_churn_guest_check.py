#!/usr/bin/env python3
"""Stage253 optical allocation-churn audit, inheriting all Stage252 proofs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage241_render_guest_check import close
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage252_stress_guest_check import verify_stress_guest

SCHEMA="foj-stage253-nexium-384-frame-compact-cache-churn-v1"
# Capture geometry: y76..83 guest becomes y75..80 in NeXium GUI.
# Avoid y81: it is unpainted background in actual guest screenshots.
ORIGIN=536
STEP=72
STATUS_X=968
Y=(76,78,80)
ON=((149,223,88),(92,180,223),(238,167,142),
    (232,210,103),(198,122,215),(242,177,220))
OFF=(48,37,48)
READY=(148,227,84)
EXPECTED=(384,48,48,192,192,3600)

def color_matches(im,x,color):
    return all(close(im.getpixel((x,y)),color) for y in Y)

def word(im,origin,on):
    value=0
    for bit in range(16):
        x=sample_x(origin+4*bit)
        if color_matches(im,x,on):
            value|=1<<bit
        elif not color_matches(im,x,OFF):
            raise ValueError(f"Stage253 invalid bit color x={x}")
    if value==65535:
        raise ValueError("Stage253 saturated optical counter")
    return value

def verify_churn_guest(paths:tuple[Path,...])->dict:
    if len(paths)!=len(STATES):
        raise ValueError("Exactly nine real NeXium states required")
    ancestor=verify_stress_guest(paths)
    receipts={}
    for state,path in zip(STATES,paths):
        im=read_frame(path)
        if not all(color_matches(im,sample_x(STATUS_X+i),READY)
                   for i in (2,3,4)):
            raise ValueError(f"{state}: missing Stage253 ready tile")
        actual=tuple(word(im,ORIGIN+72*i,ON[i]) for i in range(6))
        if actual!=EXPECTED:
            raise ValueError(f"{state}: Stage253 expected {EXPECTED}, got {actual}")
        receipts[state]=dict(zip(("frames","allocations","releases",
                                 "cache_hits","cache_misses","peak_kib"),actual))
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "actual_battle_states":len(paths),
        "test_frames_in_single_guest":EXPECTED[0],
        "synthetic_resolution_blocks":EXPECTED[1],
        "allocations":EXPECTED[1],
        "releases":EXPECTED[2],
        "hits":EXPECTED[3],
        "misses":EXPECTED[4],
        "max_single_raster_payload_kib":EXPECTED[5],
        "scene_mutations_and_repeated_hits_checked_in_guest":True,
        "per_frame_uncached_pixel_reference_checked_in_guest":True,
        "requested_pixel_payload_not_rss":True,
        "allocator_heap_fragmentation_measured":False,
        "whole_game_fps_measured":False,
        "physical_switch_tested":False,
        "original_ps3_assets_used":False,
        "default_nro_unchanged":True,
        "inherited_stage252_schema":ancestor["schema"],
        "inherited_stage251_schema":ancestor["inherited_stage251_schema"],
        "frame_sha256":ancestor["frame_sha256"],
        "states":receipts,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--"+state.replace("_","-"),type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    a=parser.parse_args()
    result=verify_churn_guest(tuple(getattr(a,s) for s in STATES))
    with a.report.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2)
        f.write("\n")
    print("Stage253 NeXium: 384 frames, 48 allocations, 48 releases, "
          "192 cache hits, 192 misses, 3600 KiB peak requested raster; "
          "9 screenshots plus Stage252 ancestors verified")

if __name__=="__main__":
    main()
