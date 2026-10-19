#!/usr/bin/env python3
"""Stage246: decode four exclusive in-guest software-render phase bars.

This is generated-only CPU-raster profiling in NeXium, not FPS or GPU time.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from tools.foj_stage231_threat_guest_check import read_frame
from tools.foj_stage238_cache_guest_check import STATES, verify_cache_screenshots
from tools.foj_stage241_render_guest_check import close, verify_render_timing

SCHEMA = "foj-stage246-nexium-four-exclusive-software-render-phases-v1"
PHASES = ("terrain", "forecast_compute", "threat_markers", "battle_hud")
X = (948, 1020, 1092, 1164)
COLORS = ((74,212,131),(235,101,66),(222,187,81),(154,127,239))
OFF = (48,37,48)
READY = (90,230,132)
Y = (13,15,17)
ACTIVE = ("selected","hovered","restored","guarded","guard_hovered")
INACTIVE = ("initial","hidden","cancelled","ended")

def sample_x(framebuffer_x: int) -> int:
    # Stage245 sampled real NeXium GUI x around
    # round(22 + .966*(guest_x+1))-1. Require one interior column.
    return round(22 + .966*(framebuffer_x+1))-1

def matches(image,x,color) -> bool:
    return all(close(image.getpixel((x,y)),color) for y in Y)

def bits(image, origin: int, on: tuple[int,int,int]) -> int:
    value = 0
    for bit in range(16):
        x = sample_x(origin+bit*4)
        if matches(image,x,on):
            value |= 1<<bit
        elif not matches(image,x,OFF):
            raise ValueError(f"Unrecognized Stage246 bar pixel {bit}, x={x}")
    if value==65535:
        raise ValueError("Saturated phase barcode")
    return value

def verify_phase_screenshots(paths: tuple[Path,...]) -> dict:
    if len(paths)!=len(STATES):
        raise ValueError("Exactly nine game-state PNGs required")
    cache = verify_cache_screenshots(paths)
    normal = verify_render_timing(paths)
    frames, sha = {}, {}
    for state,path in zip(STATES,paths):
        im = read_frame(path)
        if not all(matches(im,sample_x(1238+dx),READY) for dx in (2,3,4)):
            raise ValueError(f"{state}: missing profile-ready status tile")
        row = {name:bits(im,x,color) for name,x,color in zip(PHASES,X,COLORS)}
        row["measured_sum_us"] = sum(row.values())
        row["threat_preview_expected"] = state in ACTIVE
        if row["terrain"]<=0 or row["measured_sum_us"]<=0:
            raise ValueError(f"{state}: zero/invalid terrain or total")
        frames[state]=row
        sha[state]=hashlib.sha256(path.read_bytes()).hexdigest()
    if len(set(sha.values()))<2:
        raise ValueError("Identical screenshot replay cannot prove game sequence")
    stats = {phase:{
        "active_median_us": statistics.median(frames[s][phase] for s in ACTIVE),
        "inactive_median_us": statistics.median(frames[s][phase] for s in INACTIVE)
    } for phase in PHASES}
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "captured_game_screenshots":len(paths),
        "averaging_window_frames":32,
        "exclusive_timing_phases":list(PHASES),
        "states":frames,
        "phase_medians":stats,
        "frame_sha256":sha,
        "cache_gameplay_proof_schema":cache["schema"],
        "full_software_render_proof_schema":normal["schema"],
        "measurement_scope":"complete generated CPU software rasterizer split in four; framebuffer presentation excluded",
        "physical_switch_hardware_tested":False,
        "original_ps3_engine_tested":False,
        "original_foj_ai_verified":False,
        "switch_fps_measured":False,
        "gpu_time_measured":False,
        "end_to_end_latency_measured":False,
        "overall_game_speedup_proven":False,
    }

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    for state in STATES:
        parser.add_argument("--"+state.replace("_","-"),type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    report=verify_phase_screenshots(tuple(
        getattr(args,state) for state in STATES))
    with args.report.open("x",encoding="utf-8") as handle:
        json.dump(report,handle,sort_keys=True,indent=2)
        handle.write("\n")
    print("Stage246: exclusive AArch64 software-render phases",
          report["phase_medians"])

if __name__=="__main__":
    main()
