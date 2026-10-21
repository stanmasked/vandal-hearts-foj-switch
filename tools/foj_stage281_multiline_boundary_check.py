#!/usr/bin/env python3
"""Stage281: independent multi-scanline audit of *real* Stage280-style GPU evidence.

This module never generates a GPU frame. Synthetic Pillow frames appear only
in unit tests; four actual NeXium captures must come from the dedicated CI.
The Stage280 provenance, two-case UV shift, native receipts and DDS hashes
are rechecked in full before any new multi-row assertion is reported.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image

from tools.foj_stage280_shifted_boundary_sd import (
    CASES, FRAME_CROSSINGS, PROFILE_Y, profile_x,
)
from tools.foj_stage280_shifted_boundary_check import (
    DELTA, REFERENCE_CLEAR, normalized_opacity, verify as verify_stage280,
)

ROWS = (436, 438, 440, 442, 444)
ROW_POSITION_TOLERANCE = 4
ROW_SPREAD_TOLERANCE = 4


def inspect_rows(path: Path, case: str) -> dict:
    if case not in CASES or path.is_symlink() or not path.is_file():
        raise ValueError("Stage281 missing/unrecognized GPU frame")
    with Image.open(path) as source:
        if source.size != (1280, 720):
            raise ValueError("Stage281 incorrect framebuffer geometry")
        rgb = source.convert("RGB")
    xs = profile_x(case)
    results = {}
    for y in ROWS:
        samples = [rgb.getpixel((x, y)) for x in xs]
        levels = [normalized_opacity(sample) for sample in samples]
        if levels[0] >= .12 or levels[-1] <= .88:
            raise ValueError(f"Stage281 missing exchanged alpha endpoints y={y}")
        for sample, level in zip(samples, levels):
            if not -.07 <= level <= 1.07:
                raise ValueError(f"Stage281 out-of-envelope alpha y={y}")
            expected = tuple(REFERENCE_CLEAR[i] + level * DELTA[i]
                             for i in range(3))
            if any(abs(sample[i] - expected[i]) > 8 for i in range(3)):
                raise ValueError(f"Stage281 off-curve RGB y={y}")
        if any(levels[i + 1] + .06 < levels[i]
               for i in range(len(levels) - 1)):
            raise ValueError(f"Stage281 nonmonotone alpha y={y}")
        crossing = [x for x, level in zip(xs, levels) if level >= .5]
        if not crossing or abs(crossing[0] - FRAME_CROSSINGS[case]) > ROW_POSITION_TOLERANCE:
            raise ValueError(f"Stage281 wrong UV edge position y={y}")
        mid = [x for x, level in zip(xs, levels) if .1 < level < .9]
        if mid and (min(mid) < FRAME_CROSSINGS[case] - 8 or
                    max(mid) > FRAME_CROSSINGS[case] + 8):
            raise ValueError(f"Stage281 implausibly wide alpha edge y={y}")
        results[str(y)] = {
            "crossing_x": crossing[0],
            "profile_rgb": [list(p) for p in samples],
            "intermediate_pixel_count": len(mid),
        }
    crossings = [v["crossing_x"] for v in results.values()]
    if max(crossings) - min(crossings) > ROW_SPREAD_TOLERANCE:
        raise ValueError("Stage281 UV boundary incoherent across adjacent rows")
    return results


def verify(root: Path) -> dict:
    root = Path(root)
    # This makes Stage281 strictly additive to Stage280, not a replacement
    # for the original input-identity and two-frame native GPU audit.
    base = verify_stage280(root)
    results = {}
    for case in CASES:
        folder = root / case
        before = inspect_rows(folder / "gpu-initial.png", case)
        after = inspect_rows(folder / "gpu-later.png", case)
        if before != after:
            raise ValueError("Stage281 material rows not stable across GPU phases")
        if before[str(PROFILE_Y)]["crossing_x"] != (
            base["cases"][case]["initial"]["half_transition_x"]
        ):
            raise ValueError("Stage281 inherited Stage280 center-row discrepancy")
        results[case] = before
    expected_shift = FRAME_CROSSINGS[CASES[1]] - FRAME_CROSSINGS[CASES[0]]
    for y in ROWS:
        observed_shift = (results[CASES[1]][str(y)]["crossing_x"] -
                          results[CASES[0]][str(y)]["crossing_x"])
        if abs(observed_shift - expected_shift) > ROW_POSITION_TOLERANCE:
            raise ValueError(f"Stage281 edge displacement not UV-driven y={y}")
    return {
        "schema": "foj.stage281.real_multiline_alpha_edge.v1",
        "generated_only": True,
        "original_ps3_resources": False,
        "real_neixum_gpu_frames_required": 4,
        "rechecked_stage280_source_and_native_provenance": True,
        "row_count_per_frame": len(ROWS),
        "rows": list(ROWS),
        "sampling_mode_assumed": False,
        "physical_switch_verified": False,
        "cases": results,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        record = verify(args.evidence)
        with args.report.open("x", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except (OSError, ValueError, TypeError, KeyError) as error:
        print("Stage281 multi-row GPU evidence refused: " + str(error),
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
