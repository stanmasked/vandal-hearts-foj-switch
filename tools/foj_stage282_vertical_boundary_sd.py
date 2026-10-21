#!/usr/bin/env python3
"""Stage282: generated-only DDS with a vertical (V) transparent-to-opaque edge.

No original PS3 data. Preserve the verified native NRO, public shaders,
materials, actor, camera and depth/sort contract; only near DDS alpha varies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from tools.foj_stage273_dynamic_gpu_sd import install_dynamic
from tools.foj_stage267_generated_multiblend_sd import SUBDIR
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
from tools.foj_stage280_shifted_boundary_sd import target_rgb

SCHEMA = "foj.stage282.vertical_alpha_dds.v1"
SPLITS = {"edge-v40": 40, "edge-v52": 52}
CASES = tuple(SPLITS)
WIDTH = 64
# Native C11 projection produces Y=376.254 / 443.727 in a 1280x720
# framebuffer. The real NeXium window capture scales the game viewport to
# 694 pixels high (rows 0..693, toolbar begins at row 694), so observed
# screenshot crossings are round(native_y * 694/720) -> 363 / 428.
NATIVE_FRAME_HEIGHT = 720
CAPTURE_VIEWPORT_HEIGHT = 694
CAPTURE_VIEWPORT_PROBE_X = 1000
NATIVE_EXPECTED_Y = {"edge-v40": 376.254, "edge-v52": 443.727}
EXPECTED_Y = {"edge-v40": 363, "edge-v52": 428}
PROBE_X = 630
COLUMNS = (624, 630, 636)
ATLAS = "material0.dds"


def profile_y(case: str) -> tuple[int, ...]:
    if case not in CASES:
        raise ValueError("Unexpected Stage282 V boundary case")
    center = EXPECTED_Y[case]
    return tuple(range(center - 13, center + 14))


def positions(case: str) -> dict[str, tuple[int, int]]:
    if case not in CASES:
        raise ValueError("Unexpected Stage282 case")
    cy = EXPECTED_Y[case]
    return {"top_control": (PROBE_X, cy - 13),
            "bottom_control": (PROBE_X, cy + 13),
            "rear_only": (760, 400)}


def expected_at(case: str, label: str) -> tuple[int, int, int]:
    if label not in positions(case):
        raise ValueError("Unknown Stage282 probe")
    if label == "rear_only":
        from tools.foj_stage266_transparency_order import COOL
        return COOL
    return target_rgb(0 if label == "top_control" else 255)


def near_atlas(case: str) -> bytes:
    if case not in CASES:
        raise ValueError("Unexpected Stage282 V boundary case")
    original = generated_dds((*VIOLET, 128))
    buf = bytearray(original)
    if len(buf) != 128 + WIDTH * WIDTH * 4:
        raise ValueError("Unexpected generated DDS layout")
    for y in range(WIDTH):
        alpha = 0 if y < SPLITS[case] else 255
        for x in range(WIDTH):
            buf[128 + (y * WIDTH + x) * 4 + 3] = alpha
    return bytes(buf)


def install_masked(root: Path, shaders: Path, case: str) -> dict:
    if case not in CASES:
        raise ValueError("Unknown Stage282 case")
    original = generated_dds((*VIOLET, 128))
    masked = near_atlas(case)
    if (len(masked) != len(original) or masked[:128] != original[:128]
            or any(masked[i] != original[i]
                   for i in range(128, len(masked)) if (i - 128) % 4 != 3)
            or sum(a != b for a, b in zip(masked, original)) != WIDTH * WIDTH):
        raise ValueError("Stage282 source changed non-alpha pixels or header")
    root = Path(root)
    report = install_dynamic(root, shaders, "original")
    target = root / SUBDIR / ATLAS
    if target.is_symlink() or not target.is_file() or target.read_bytes() != original:
        raise ValueError("Stage282 generated baseline not byte-exact")
    target.write_bytes(masked)
    if target.read_bytes() != masked:
        raise ValueError("Stage282 failed to install DDS")
    report.update({
        "schema": SCHEMA, "scenario": case, "changed_file": ATLAS,
        "generated_only": True, "original_ps3_resources": False,
        "actual_gpu_render_verified": False,
        "near_dds_sha256": hashlib.sha256(masked).hexdigest(),
        "near_original_dds_sha256": hashlib.sha256(original).hexdigest(),
        "near_alpha_split_y": SPLITS[case],
        "expected_half_transition_y": EXPECTED_Y[case],
        "native_expected_half_transition_y": NATIVE_EXPECTED_Y[case],
        "native_framebuffer_height": NATIVE_FRAME_HEIGHT,
        "capture_viewport_height": CAPTURE_VIEWPORT_HEIGHT,
        "capture_viewport_probe_x": CAPTURE_VIEWPORT_PROBE_X,
        "capture_scale_y": round(CAPTURE_VIEWPORT_HEIGHT / NATIVE_FRAME_HEIGHT, 8),
        "near_texture_dimensions": [WIDTH, WIDTH],
        "profile_x_columns": list(COLUMNS),
        "profile_y_positions": list(profile_y(case)),
        "probe_x": PROBE_X,
        "expected_native_pass_order": [2, 1, 0],
        "expected_probe_rgb": {
            key: list(expected_at(case, key)) for key in positions(case)
        },
        "profile_goal": "verify V-driven displacement without assuming GPU filtering",
    })
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--shaders", required=True, type=Path)
    parser.add_argument("--case", required=True, choices=CASES)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(install_masked(args.data_root, args.shaders, args.case),
                         sort_keys=True))
    except (OSError, ValueError) as exc:
        print("Stage282 generated DDS rejected: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
