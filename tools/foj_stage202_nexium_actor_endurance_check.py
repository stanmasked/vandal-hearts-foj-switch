#!/usr/bin/env python3
"""Stage 202: verify actual NeXium guest screenshots across generated A/B/A cycles.

Reuses Stage 201 guest image parser, which verifies the real NRO's SD
load, accepted secondary clip, amber research marker and visible wire.
This test cannot verify original PS3 motion or private user assets.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

SCHEMA="foj.stage202.generated_sd_actor_endurance.v1"


def labels(cycles):
    if type(cycles) is not int or not 3<=cycles<=8:
        raise ValueError("Unsupported NeXium endurance cycle count")
    return ("baseline",)+tuple(
        f"{state}-{cycle:02d}"
        for cycle in range(1,cycles+1)
        for state in ("reset","a-step","a-paused","b-complete","a-return")
    )


def read_rss(path:Path, cycles:int):
    lines=path.read_text(encoding="ascii").splitlines()
    if len(lines)!=cycles+1:
        raise ValueError("Missing host RSS checkpoints")
    kib=[]
    for i,line in enumerate(lines):
        pieces=line.split("\t")
        if (len(pieces)!=2 or pieces[0]!=f"{i:02d}" or
                not pieces[1].isdigit()):
            raise ValueError("Invalid host RSS sequence")
        value=int(pieces[1])
        if not 1000<=value<=8*1024*1024:
            raise ValueError("Host RSS outside safe measurement range")
        kib.append(value)
    return kib


def check_records(records, rss, cycles):
    expected=labels(cycles)
    if set(records)!=set(expected):
        raise ValueError("Missing or unexpected guest screenshots")
    dimensions={tuple(info[0]) for info in records.values()}
    if len(dimensions)!=1:
        raise ValueError("Guest screenshot geometry changed")
    if len(rss)!=cycles+1:
        raise ValueError("Host RSS checkpoints missing")
    for label in expected:
        _size,markers,wire=records[label]
        if len(wire)<40:
            raise ValueError("Missing guest wireframe")
        if (markers["original_data_experimental"]<350 or
            markers["secondary_accepted"]<300 or
            markers["secondary_rejected"]>100 or
            markers["crossfade"]>120):
            raise ValueError("Bad research SD, secondary or crossfade marker")

    def difference(left,right):
        return len(records[left][2] ^ records[right][2])

    # Switch R after a reset must move A; an intentional wall-clock pause
    # must not change that pose; Y + four steps must animate A -> B -> A.
    motion_a,motion_b,motion_back=[],[],[]
    stillness=[]
    across_cycle=[]
    for cycle in range(1,cycles+1):
        suffix=f"{cycle:02d}"
        reset=f"reset-{suffix}"
        play=f"a-step-{suffix}"
        paused=f"a-paused-{suffix}"
        b=f"b-complete-{suffix}"
        a=f"a-return-{suffix}"
        if difference("baseline",reset)>30:
            raise ValueError("Reset did not return to original A bind frame")
        pause_delta=difference(play,paused)
        if pause_delta>30:
            raise ValueError("Paused guest unexpectedly advanced the rig")
        stillness.append(pause_delta)
        ma=difference(reset,play)
        mb=difference(play,b)
        mr=difference(b,a)
        if min(ma,mb,mr)<45:
            raise ValueError("Generated A/B/A guest transition stopped moving")
        motion_a.append(ma)
        motion_b.append(mb)
        motion_back.append(mr)
        if cycle>1:
            previous=f"{cycle-1:02d}"
            comparisons=(
                (f"reset-{previous}",reset),
                (f"a-step-{previous}",play),
                (f"b-complete-{previous}",b),
                (f"a-return-{previous}",a)
            )
            differences=[difference(left,right) for left,right in comparisons]
            if max(differences)>35:
                raise ValueError("Identical synthetic A/B/A cycle no longer repeats")
            across_cycle.extend(differences)
    # Deliberately coarse host process leak warning; memory can fluctuate.
    # Do not claim leak freedom from a small emulated test.
    maximum=max(rss)
    if maximum > 2*rss[0]+128*1024:
        raise ValueError("Host RSS exceeded coarse endurance safety budget")

    return {
        "schema":SCHEMA,
        "environment":"NeXium_genuine_actor_NRO_generated_only_virtual_SD",
        "cycles_verified":cycles,
        "guest_frames_verified":len(expected),
        "captured_real_emulator_frames":True,
        "unique_guest_dimensions":list(next(iter(dimensions))),
        "per_cycle_a_motion_pixels":motion_a,
        "per_cycle_a_to_b_pixels":motion_b,
        "per_cycle_b_to_a_pixels":motion_back,
        "max_paused_guest_changed_pixels":max(stillness),
        "max_intercycle_repetition_changed_pixels":max(across_cycle,default=0),
        "host_rss_initial_kib":rss[0],
        "host_rss_peak_kib":maximum,
        "host_rss_final_kib":rss[-1],
        "rss_leak_freedom_proven":False,
        "original_ps3_resources_used":False,
        "original_game_animation_fidelity_verified":False,
        "physical_switch_tested":False,
    }


def verify(folder:Path, cycles:int=6):
    # Import Pillow only when processing actual emulator screenshots. Native
    # host unit tests use the pure check_records() function without Pillow.
    from tools.foj_stage201_nexium_sd_actor_frame_check import inspect_image
    names=labels(cycles)
    found={name:inspect_image(folder/f"endurance-{name}.png")
           for name in names}
    return check_records(
        found,read_rss(folder/"endurance-generated-host-rss.tsv",cycles),
        cycles
    )


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--cycles",type=int,default=6)
    args=parser.parse_args(argv)
    try:
        report=verify(args.evidence,args.cycles)
        with args.report.open("x",encoding="utf-8") as target:
            json.dump(report,target,indent=2,sort_keys=True)
            target.write("\n")
    except (OSError,ValueError):
        parser.error("Generated-only NeXium actor endurance failed")
    print("Stage 202 NeXium generated actor endurance guest: verified.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
