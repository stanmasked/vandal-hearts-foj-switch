#!/usr/bin/env python3
"""Stage267 independent probe verifier for NeXium screenshots (not fake proof).

The CI workflow captures the image from a running GPU guest. This module only
validates supplied PNG content; synthesized PIL test fixtures are unit tests,
never a substitute for actual emulator provenance.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops
from tools.foj_stage267_generated_multiblend_sd import CASES, expected_rgb
from tools.foj_stage266_transparency_order import COOL

SCHEMA = "foj.stage267.gpu_three_layer_guest.v1"
FRAMES = ("gpu-initial.png", "gpu-later.png")
PROBES = {"overlap": (640, 400), "overlap_other": (600, 400),
          "rear_only": (760, 400)}
BACKGROUNDS = ((25,350), (1220,350), (640,650), (25,650))
TOLERANCE = 8
MIN_CORRECT = 116


def inspect(path: Path, case: str) -> dict:
    if case not in CASES:
        raise ValueError("Unknown scene case")
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    if rgb.size != (1280, 720):
        raise ValueError("Unexpected NeXium framebuffer size")
    px = rgb.load()
    readings = {}
    for name, (x, y) in PROBES.items():
        target = COOL if name == "rear_only" else expected_rgb(case)
        samples = [px[xx,yy] for yy in range(y-5,y+6)
                   for xx in range(x-5,x+6)]
        count = sum(all(abs(rgb[i]-target[i]) <= TOLERANCE for i in range(3))
                    for rgb in samples)
        if count < MIN_CORRECT:
            raise ValueError(f"{case} {name}: {count}/121 correct RGB pixels")
        readings[name] = {
            "pixel": [x,y], "expected_rgb": list(target),
            "matching_pixels": count, "tolerance": TOLERANCE,
        }
    return readings


def verify(root: Path) -> dict:
    inspected = {}
    signatures = []
    for case in CASES:
        folder = root / case
        first = inspect(folder / FRAMES[0], case)
        later = inspect(folder / FRAMES[1], case)
        if [first[name]["matching_pixels"] for name in PROBES] != [
            later[name]["matching_pixels"] for name in PROBES
        ]:
            raise ValueError("Material footprints varied across GPU frames")
        with Image.open(folder / FRAMES[0]) as a, Image.open(folder / FRAMES[1]) as b:
            x, y = a.convert("RGB"), b.convert("RGB")
        if ImageChops.difference(x,y).getbbox() is None:
            raise ValueError("Duplicate GPU screenshot")
        if sum(x.getpixel(p) != y.getpixel(p) for p in BACKGROUNDS) < 3:
            raise ValueError("No changed GPU clear-color phase")
        signatures.append(tuple(x.getpixel(PROBES["overlap"])))
        inspected[case] = {
            "first": first, "second": later,
            "background_phase_changed": True,
        }
    if len(set(signatures)) != len(CASES):
        raise ValueError("Two alpha cases produced indistinguishable overlap")
    return {
        "schema": SCHEMA,
        "screenshot_files_inspected": 2 * len(CASES),
        "actual_guest_capture_provenance": "requires separate GitHub Actions NeXium runner",
        "generated_only": True,
        "original_ps3_resources": False,
        "physical_switch_verified": False,
        "three_layer_rgba_controls_verified": True,
        "expected_overlap_rgb": {case: list(expected_rgb(case)) for case in CASES},
        "cases": inspected,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    opts = parser.parse_args(argv)
    try:
        result = verify(opts.evidence)
        with opts.report.open("x", encoding="utf-8") as output:
            json.dump(result, output, indent=2, sort_keys=True)
            output.write("\n")
    except (OSError, ValueError) as exc:
        parser.error("Stage267 three-layer GPU pixel proof failed: " + str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
