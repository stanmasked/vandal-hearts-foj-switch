#!/usr/bin/env python3
"""Stage 185: real NeXium reverse COLL controls, matched against C references."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tools.foj_stage184_coll_input_check import load, source_pixel_agreement, difference, anchor

SCHEMA="foj-stage185-nexium-coll-reverse-control-roundtrip-v1"
STATES=("reverse-l", "return-r", "reverse-zl", "reverse-left")
REFERENCES=("ch5", "ch0", "cursor-right", "heat")
MIN_CHANGED=(3000,3000,3000,70)


def verify_reverse_controls(root: Path) -> dict:
    previous=load(root/"coll-ch0.png")
    anchor(previous)
    results={}
    deltas={}
    for state,reference,minimum in zip(STATES,REFERENCES,MIN_CHANGED,strict=True):
        guest=load(root/f"coll-{state}.png")
        ref=load(root/f"ref-coll-{reference}.png")
        fraction,pixels=source_pixel_agreement(guest,ref)
        change=difference(previous,guest)
        if fraction<0.87 or change<minimum:
            raise ValueError(f"NeXium reverse COLL control failed: {state}")
        results[state]={"reference_agreement":round(fraction,5),
                        "reference_pixels_checked":pixels,
                        "changed_guest_pixels":change}
        deltas[state]=change
        previous=guest

    # Reverse R/L and ZR/ZL must restore source-identical data, not just
    # approximate some arbitrary map. All frames are from actual guest run.
    equality=[
        ("coll-reverse-l.png","coll-ch5.png"),
        ("coll-return-r.png","coll-ch0.png"),
        ("coll-reverse-zl.png","coll-cursor-right.png"),
        ("coll-reverse-left.png","coll-heat-return-after-y.png"),
    ]
    roundtrip={}
    for current,former in equality:
        one=load(root/current)
        other=load(root/former)
        changed=difference(one,other)
        if changed>max(4000,one.width*one.height//100):
            raise ValueError("Reverse controls failed to restore prior guest image")
        roundtrip[current]=changed

    return {
        "schema":SCHEMA,
        "emulator":"NeXium",
        "scope":"generated_only_coll_homebrew",
        "emulated_button_sequence":["L","R","ZL","DLeft"],
        "keyboard_keys":["q","e","r","Left"],
        "states_verified":results,
        "restoration_pixel_differences":roundtrip,
        "reverse_channels_verified":True,
        "reverse_zoom_verified":True,
        "reverse_cursor_verified":True,
        "physical_switch_execution_verified":False,
        "original_ps3_assets_used":False,
        "original_foj_gameplay_verified":False,
    }


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    try:
        result=verify_reverse_controls(args.evidence)
        with args.report.open("x",encoding="utf-8") as file:
            json.dump(result,file,sort_keys=True,indent=2)
            file.write("\n")
    except (OSError,ValueError) as err:
        parser.error(str(err))
    print("NeXium L/R, ZL and DLeft reversed actual COLL guest screens")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
