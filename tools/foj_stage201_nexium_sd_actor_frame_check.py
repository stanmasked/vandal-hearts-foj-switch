#!/usr/bin/env python3
"""Stage 201: verify *actual guest frames* of generated-only FOJRM001/BANIM NRO.

Rejects missing SD asset markers, absent geometry, frozen playback,
pause drift, bad fade markers or altered reset. Synthetic fixture files are
created separately; no original PS3 data is accepted in public CI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from PIL import Image

SCHEMA="foj.stage201.generated_sd_guest.v1"
STATES=(
    "initial","step-025","still-025","reset","fade-0",
    "fade-25","fade-50","fade-75","fade-done","reset-after"
)
COLORS={
    "original_data_experimental":(233,182,87),
    "secondary_accepted":(0,136,255),
    "secondary_rejected":(255,0,0),
    "crossfade":(255,255,0),
    "wire":(218,228,189),
}


def near(pixel,color,tol=17):
    return all(abs(int(p)-v)<=tol for p,v in zip(pixel,color))


def inspect_image(path:Path):
    with Image.open(path) as img:
        rgb=img.convert("RGB")
    w,h=rgb.size
    if w<1100 or h<620 or w>2200 or h>1500:
        raise ValueError("Unexpected NeXium guest screenshot resolution")
    values=rgb.load()
    marks={name:0 for name in COLORS if name!="wire"}
    strokes=set()
    for y in range(h):
        for x in range(w):
            pixel=values[x,y]
            if y<max(100,int(h*.22)):
                for name in marks:
                    if near(pixel,COLORS[name]):
                        marks[name]+=1
            elif (int(.15*w)<x<int(.85*w) and y<int(h*.94) and
                  near(pixel,COLORS["wire"],12)):
                strokes.add((x,y))
    if len(strokes)<40:
        raise ValueError("Research rig geometry not visible; SD mount may have failed")
    if marks["original_data_experimental"]<350:
        raise ValueError("Research rig marker absent; guest may be missing assets")
    if marks["secondary_accepted"]<300 or marks["secondary_rejected"]>100:
        raise ValueError("Secondary synthesized BANIM not accepted in guest")
    return (w,h),marks,strokes


def verify(evidence:Path):
    frames={name:inspect_image(evidence/f"rig-{name}.png") for name in STATES}
    dims={item[0] for item in frames.values()}
    if len(dims)!=1:
        raise ValueError("Guest framebuffer dimensions changed across states")
    for name,item in frames.items():
        fade=name in ("fade-0","fade-25","fade-50","fade-75")
        if fade and item[1]["crossfade"]<300:
            raise ValueError("Incoming crossfade not shown: "+name)
        if not fade and item[1]["crossfade"]>120:
            raise ValueError("Unexpected crossfade marker: "+name)

    def diff(a,b):
        return len(frames[a][2] ^ frames[b][2])

    # We compare actual rasterized wire segments, excluding the screen
    # status blocks at top; no screenshot is fabricated or inferred.
    still=diff("step-025","still-025")
    start_reset=diff("initial","reset")
    fade_start=diff("reset","fade-0")
    after_reset=diff("initial","reset-after")
    if still>30 or start_reset>30 or fade_start>30 or after_reset>30:
        raise ValueError("Paused/reset/zero-crossfade geometry changed")
    motion=diff("initial","step-025")
    if motion<65:
        raise ValueError("R key did not advance live original-data actor mesh")
    fades=[]
    for a,b in (
        ("fade-0","fade-25"),("fade-25","fade-50"),
        ("fade-50","fade-75"),("fade-75","fade-done")
    ):
        amount=diff(a,b)
        if amount<45:
            raise ValueError("Crossfade mesh did not move: "+a+" / "+b)
        fades.append(amount)
    if diff("initial","fade-done")<65:
        raise ValueError("Secondary clip produced no observable new pose")
    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "scope":"real_actor_research_nro_with_generated_only_sd_data",
        "frames_verified":len(STATES),
        "guest_frame_dimensions":list(next(iter(dims))),
        "generated_secondary_asset_accepted":True,
        "guest_research_amber_marker_confirmed":True,
        "initial_motion_changed_pixels":motion,
        "paused_stillness_changed_pixels":still,
        "reset_changed_pixels":start_reset,
        "initial_crossfade_zero_changed_pixels":fade_start,
        "crossfade_changed_pixels":fades,
        "after_final_reset_changed_pixels":after_reset,
        "original_game_assets_included":False,
        "original_ps3_animation_accuracy_verified":False,
        "actual_original_ps3_model_loaded":False,
        "physical_switch_executed":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",required=True,type=Path)
    parser.add_argument("--report",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        result=verify(args.evidence)
        with args.report.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2,sort_keys=True)
            f.write("\n")
    except (ValueError,OSError):
        parser.error("Generated NeXium SD guest comparison failed")
    print("Stage 201: original-capable NRO loaded generated SD rig and dual BANIM.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
