#!/usr/bin/env python3
"""Stage284: generated-only DDS with simultaneous orthogonal U/V alpha edges."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from tools.foj_stage273_dynamic_gpu_sd import install_dynamic
from tools.foj_stage267_generated_multiblend_sd import SUBDIR
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import COOL, VIOLET
from tools.foj_stage280_shifted_boundary_sd import target_rgb

SCHEMA = "foj.stage284.uv_cross_alpha_dds.v1"
CASE = "uv-cross"
WIDTH = 64
SPLIT_U = 46
SPLIT_V = 46
U_EXPECTED_X = 649
V_EXPECTED_Y = 395
U_PROFILE_ROWS = (439, 440, 441)
U_PROFILE_X = tuple(range(636, 663))
V_PROFILE_COLUMNS = (682, 684, 686)
V_PROFILE_Y = tuple(range(382, 409))
CAPTURE_VIEWPORT_HEIGHT = 694
CAPTURE_VIEWPORT_PROBE_X = 1000
PROBE_X = 630
ATLAS = "material0.dds"
CONTROL_POSITIONS = {
    "u_left": (636, 440), "u_right": (662, 440),
    "v_top": (683, 382), "v_bottom": (683, 408),
    "rear_only": (760, 400),
}


def expected_at(label: str) -> tuple[int, int, int]:
    if label in ("u_left", "v_top"):
        return target_rgb(0)
    if label in ("u_right", "v_bottom"):
        return target_rgb(255)
    if label == "rear_only":
        return COOL
    raise ValueError("Unknown Stage284 probe")


def near_atlas(case: str = CASE) -> bytes:
    if case != CASE:
        raise ValueError("Unknown Stage284 DDS case")
    baseline = generated_dds((*VIOLET, 128))
    if len(baseline) != 128 + WIDTH * WIDTH * 4:
        raise ValueError("Unexpected generated DDS layout")
    buf = bytearray(baseline)
    for y in range(WIDTH):
        for x in range(WIDTH):
            alpha = 255 if x >= SPLIT_U and y >= SPLIT_V else 0
            buf[128 + (y * WIDTH + x) * 4 + 3] = alpha
    return bytes(buf)


def install_masked(root: Path, shaders: Path) -> dict:
    root = Path(root)
    original = generated_dds((*VIOLET, 128))
    masked = near_atlas()
    if (len(masked) != len(original) or masked[:128] != original[:128]
            or any(masked[i] != original[i]
                   for i in range(128, len(masked)) if (i - 128) % 4 != 3)
            or sum(a != b for a, b in zip(masked, original)) != WIDTH * WIDTH):
        raise ValueError("Stage284 changed non-alpha DDS bytes or split count")
    receipt = install_dynamic(root, shaders, "original")
    target = root / SUBDIR / ATLAS
    if target.is_symlink() or not target.is_file() or target.read_bytes() != original:
        raise ValueError("Stage284 generated baseline is not byte-exact")
    target.write_bytes(masked)
    if target.read_bytes() != masked:
        raise ValueError("Stage284 failed to install combined UV mask")
    receipt.update({
        "schema": SCHEMA, "scenario": CASE, "changed_file": ATLAS,
        "generated_only": True, "original_ps3_resources": False,
        "actual_gpu_render_verified": False,
        "near_original_dds_sha256": hashlib.sha256(original).hexdigest(),
        "near_dds_sha256": hashlib.sha256(masked).hexdigest(),
        "near_alpha_split_u": SPLIT_U, "near_alpha_split_v": SPLIT_V,
        "expected_half_transition_x": U_EXPECTED_X,
        "expected_half_transition_y": V_EXPECTED_Y,
        "near_texture_dimensions": [WIDTH, WIDTH],
        "u_profile_rows": list(U_PROFILE_ROWS),
        "u_profile_x_positions": list(U_PROFILE_X),
        "v_profile_columns": list(V_PROFILE_COLUMNS),
        "v_profile_y_positions": list(V_PROFILE_Y),
        "capture_viewport_height": CAPTURE_VIEWPORT_HEIGHT,
        "capture_viewport_probe_x": CAPTURE_VIEWPORT_PROBE_X,
        "probe_x": PROBE_X,
        "control_probe_positions": {k: list(v) for k, v in CONTROL_POSITIONS.items()},
        "expected_native_pass_order": [2, 1, 0],
        "expected_probe_rgb": {k: list(expected_at(k)) for k in CONTROL_POSITIONS},
        "profile_goal": "verify orthogonal U and V alpha edges simultaneously in one generated DDS without assuming sampler filtering",
    })
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--shaders", required=True, type=Path)
    parser.add_argument("--case", choices=(CASE,), required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(install_masked(args.data_root, args.shaders), sort_keys=True))
    except (OSError, ValueError) as exc:
        print("Stage284 generated UV-cross DDS rejected: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
