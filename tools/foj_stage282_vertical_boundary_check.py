#!/usr/bin/env python3
"""Stage282 independent physical-color auditor for vertical DDS-V alpha edges.

Host-created mock PNGs exercise this code only. Runtime proof needs four
original actual NeXium window captures and native receipts from the guest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
from tools.foj_stage267_gpu_three_layer_check import BACKGROUNDS
from tools.foj_stage274_pass_contract_check import expected_receipt
from tools.foj_stage280_shifted_boundary_check import (
    REFERENCE_CLEAR, DELTA, normalized_opacity, ENDPOINT_TOLERANCE,
    ENDPOINT_MIN_MATCH, file_bytes,
)
from tools.foj_stage282_vertical_boundary_sd import (
    SCHEMA, CASES, SPLITS, WIDTH, COLUMNS, PROBE_X, EXPECTED_Y,
    positions, profile_y, expected_at, near_atlas,
)

CROSSING_TOLERANCE = 5
DISPLACEMENT_TOLERANCE = 6
COLUMN_SPREAD = 4


def inspect(path: Path, case: str) -> dict:
    if case not in CASES or path.is_symlink() or not path.is_file():
        raise ValueError("Stage282 missing guest PNG or invalid scenario")
    with Image.open(path) as source:
        if source.size != (1280, 720):
            raise ValueError("Stage282 unexpected NeXium framebuffer size")
        image = source.convert("RGB")
    controls = {}
    for name, (cx, cy) in positions(case).items():
        want = expected_at(case, name)
        count = sum(
            all(abs(image.getpixel((x, y))[i] - want[i]) <= ENDPOINT_TOLERANCE
                for i in range(3))
            for x in range(cx - 4, cx + 5)
            for y in range(cy - 4, cy + 5)
        )
        if count < ENDPOINT_MIN_MATCH:
            raise ValueError(f"Stage282 invalid RGB control {case}/{name}")
        controls[name] = {"expected_rgb": list(want), "matching_pixels": count}
    columns = {}
    for x in COLUMNS:
        pixels = [image.getpixel((x, y)) for y in profile_y(case)]
        opacity = [normalized_opacity(pixel) for pixel in pixels]
        if not (opacity[0] < .12 and opacity[-1] > .88):
            raise ValueError(f"Stage282 vertical alpha endpoints not exchanged x={x}")
        for rgb, level in zip(pixels, opacity):
            if not -.07 <= level <= 1.07:
                raise ValueError(f"Stage282 out-of-envelope alpha x={x}")
            ideal = tuple(REFERENCE_CLEAR[i] + level * DELTA[i]
                          for i in range(3))
            if any(abs(rgb[i] - ideal[i]) > 8 for i in range(3)):
                raise ValueError(f"Stage282 off-curve RGB x={x}")
        if any(opacity[i + 1] + .06 < opacity[i]
               for i in range(len(opacity) - 1)):
            raise ValueError(f"Stage282 nonmonotone vertical alpha x={x}")
        crossing = [y for y, level in zip(profile_y(case), opacity)
                    if level >= .5]
        if not crossing or abs(crossing[0] - EXPECTED_Y[case]) > CROSSING_TOLERANCE:
            raise ValueError(f"Stage282 V boundary at unexpected Y x={x}")
        intermediate = [y for y, level in zip(profile_y(case), opacity)
                        if .1 < level < .9]
        if intermediate and (min(intermediate) < EXPECTED_Y[case] - 8 or
                             max(intermediate) > EXPECTED_Y[case] + 8):
            raise ValueError(f"Stage282 physically implausible broad edge x={x}")
        columns[str(x)] = {
            "half_transition_y": crossing[0],
            "profile_rgb": [list(value) for value in pixels],
            "estimated_alpha": [round(value, 4) for value in opacity],
            "intermediate_sample_count": len(intermediate),
        }
    crossings = [c["half_transition_y"] for c in columns.values()]
    if max(crossings) - min(crossings) > COLUMN_SPREAD:
        raise ValueError("Stage282 V boundary drifts across columns")
    return {"controls": controls, "columns": columns,
            "sampler_filter_mode": "NOT_INFERRED"}


def verify(root: Path) -> dict:
    root = Path(root)
    cases = {}
    pristine = generated_dds((*VIOLET, 128))
    for case in CASES:
        folder = root / case
        manifest = json.loads(file_bytes(folder / "generated-input.json"))
        expected = near_atlas(case)
        digest = hashlib.sha256(expected).hexdigest()
        baseline_digest = hashlib.sha256(pristine).hexdigest()
        want_probes = {name: list(expected_at(case, name))
                       for name in positions(case)}
        if (manifest.get("schema") != SCHEMA
                or manifest.get("scenario") != case
                or manifest.get("changed_file") != "material0.dds"
                or manifest.get("generated_only") is not True
                or manifest.get("original_ps3_resources") is not False
                or manifest.get("actual_gpu_render_verified") is not False
                or manifest.get("near_dds_sha256") != digest
                or manifest.get("near_original_dds_sha256") != baseline_digest
                or manifest.get("near_alpha_split_y") != SPLITS[case]
                or manifest.get("expected_half_transition_y") != EXPECTED_Y[case]
                or manifest.get("near_texture_dimensions") != [WIDTH, WIDTH]
                or manifest.get("profile_x_columns") != list(COLUMNS)
                or manifest.get("profile_y_positions") != list(profile_y(case))
                or manifest.get("probe_x") != PROBE_X
                or manifest.get("expected_native_pass_order") != [2, 1, 0]
                or manifest.get("expected_probe_rgb") != want_probes
                or manifest.get("profile_goal") !=
                "verify V-driven displacement without assuming GPU filtering"):
            raise ValueError("Stage282 vertical source DDS provenance mismatch")
        for phase in ("before", "after"):
            if file_bytes(folder / f"near-dds-{phase}.sha256") != (
                    digest + "\n").encode("ascii"):
                raise ValueError("Stage282 DDS mutated or source receipt invalid")
        if (file_bytes(folder / "native-sort-pass.txt") !=
                b"FOJ_NATIVE_SORT_V1 2,1,0\n"
                or file_bytes(folder / "native-alpha-pass.txt") !=
                expected_receipt("original")):
            raise ValueError("Stage282 native GPU draw/pass witness invalid")
        file_bytes(folder / "guest.log")
        for marker in ("native-rear-alpha-reject.txt",
                       "native-topology-reject.txt"):
            forbidden = folder / marker
            if forbidden.exists() or forbidden.is_symlink():
                raise ValueError("Stage282 contradictory native rejection")
        first = inspect(folder / "gpu-initial.png", case)
        second = inspect(folder / "gpu-later.png", case)
        with Image.open(folder / "gpu-initial.png") as im1, Image.open(
                folder / "gpu-later.png") as im2:
            a, b = im1.convert("RGB"), im2.convert("RGB")
        if ImageChops.difference(a, b).getbbox() is None:
            raise ValueError("Stage282 duplicate framebuffer images")
        if sum(a.getpixel(p) != b.getpixel(p) for p in BACKGROUNDS) < 3:
            raise ValueError("Stage282 unchanged GPU clear-color phase")
        if first != second:
            raise ValueError("Stage282 material boundary or control changed between frames")
        cases[case] = {"initial": first, "later": second}
    delta = EXPECTED_Y[CASES[1]] - EXPECTED_Y[CASES[0]]
    for x in COLUMNS:
        y1 = cases[CASES[0]]["initial"]["columns"][str(x)]["half_transition_y"]
        y2 = cases[CASES[1]]["initial"]["columns"][str(x)]["half_transition_y"]
        if abs((y2 - y1) - delta) > DISPLACEMENT_TOLERANCE:
            raise ValueError(f"Stage282 GPU V displacement rejected at X={x}")
    return {
        "schema": "foj.stage282.real_native_vertical_v_edge.v1",
        "generated_only": True, "original_ps3_resources": False,
        "real_neixum_frames_required": 4,
        "profile_sample_count": len(CASES) * 2 * len(COLUMNS) *
                                len(profile_y(CASES[0])),
        "native_pass_receipts_checked": True,
        "sampler_filter_mode": "NOT_INFERRED",
        "physical_switch_verified": False,
        "cases": cases,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = verify(args.evidence)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Stage282 GPU evidence refused: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
