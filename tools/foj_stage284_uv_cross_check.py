#!/usr/bin/env python3
"""Stage284 independent auditor for orthogonal U/V alpha edges in one DDS."""
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
from tools.foj_stage280_shifted_boundary_sd import target_rgb
from tools.foj_stage284_uv_cross_sd import (
    SCHEMA, CASE, WIDTH, SPLIT_U, SPLIT_V, U_EXPECTED_X, V_EXPECTED_Y,
    U_PROFILE_ROWS, U_PROFILE_X, V_PROFILE_COLUMNS, V_PROFILE_Y,
    CAPTURE_VIEWPORT_HEIGHT, CAPTURE_VIEWPORT_PROBE_X,
    CONTROL_POSITIONS, expected_at, near_atlas,
)

CROSSING_TOLERANCE = 4
COLUMN_SPREAD = 4


def _inspect_profile(pixels, coordinates, expected_crossing, axis, label):
    opacity = [normalized_opacity(pixel) for pixel in pixels]
    if not (opacity[0] < .12 and opacity[-1] > .88):
        raise ValueError(f"Stage284 {axis} edge endpoints not exchanged: {label}")
    for rgb, level in zip(pixels, opacity):
        if not -.07 <= level <= 1.07:
            raise ValueError(f"Stage284 {axis} alpha outside physical envelope: {label}")
        ideal = tuple(REFERENCE_CLEAR[i] + level * DELTA[i] for i in range(3))
        if any(abs(rgb[i] - ideal[i]) > 8 for i in range(3)):
            raise ValueError(f"Stage284 {axis} RGB off source-over curve: {label}")
    if any(opacity[i + 1] + .06 < opacity[i]
           for i in range(len(opacity) - 1)):
        raise ValueError(f"Stage284 nonmonotone {axis} edge: {label}")
    crossing = [coordinate for coordinate, level in zip(coordinates, opacity)
                if level >= .5]
    if not crossing or abs(crossing[0] - expected_crossing) > CROSSING_TOLERANCE:
        raise ValueError(f"Stage284 {axis} crossing at unexpected coordinate: {label}")
    intermediate = [coordinate for coordinate, level in zip(coordinates, opacity)
                    if .1 < level < .9]
    if intermediate and (min(intermediate) < expected_crossing - 8 or
                         max(intermediate) > expected_crossing + 8):
        raise ValueError(f"Stage284 implausibly broad {axis} transition: {label}")
    return {
        "half_transition": crossing[0],
        "profile_rgb": [list(value) for value in pixels],
        "estimated_alpha": [round(value, 4) for value in opacity],
        "intermediate_sample_count": len(intermediate),
    }


def inspect(path: Path, case: str = CASE) -> dict:
    if case != CASE:
        raise ValueError("Stage284 unexpected scenario")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage284 real GPU capture missing or linked")
    with Image.open(path) as source:
        image = source.convert("RGB")
    if image.size != (1280, 720):
        raise ValueError("Stage284 unexpected NeXium capture dimensions")
    top_background = image.getpixel((CAPTURE_VIEWPORT_PROBE_X, 0))
    viewport_height = next(
        (y for y in range(1, image.height)
         if image.getpixel((CAPTURE_VIEWPORT_PROBE_X, y)) != top_background),
        image.height,
    )
    if viewport_height != CAPTURE_VIEWPORT_HEIGHT:
        raise ValueError("Stage284 capture viewport scale changed")
    controls = {}
    for name, (cx, cy) in CONTROL_POSITIONS.items():
        want = expected_at(name)
        count = sum(
            all(abs(image.getpixel((x, y))[i] - want[i]) <= ENDPOINT_TOLERANCE
                for i in range(3))
            for x in range(cx - 4, cx + 5)
            for y in range(cy - 4, cy + 5)
        )
        if count < ENDPOINT_MIN_MATCH:
            raise ValueError(f"Stage284 invalid control region {name}")
        controls[name] = {"expected_rgb": list(want), "matching_pixels": count}
    u_profiles = {}
    for y in U_PROFILE_ROWS:
        pixels = [image.getpixel((x, y)) for x in U_PROFILE_X]
        u_profiles[str(y)] = _inspect_profile(
            pixels, U_PROFILE_X, U_EXPECTED_X, "U", f"row={y}"
        )
    u_crossings = [value["half_transition"] for value in u_profiles.values()]
    if max(u_crossings) - min(u_crossings) > COLUMN_SPREAD:
        raise ValueError("Stage284 U boundary is not coherent across rows")
    v_profiles = {}
    for x in V_PROFILE_COLUMNS:
        pixels = [image.getpixel((x, y)) for y in V_PROFILE_Y]
        v_profiles[str(x)] = _inspect_profile(
            pixels, V_PROFILE_Y, V_EXPECTED_Y, "V", f"column={x}"
        )
    v_crossings = [value["half_transition"] for value in v_profiles.values()]
    if max(v_crossings) - min(v_crossings) > COLUMN_SPREAD:
        raise ValueError("Stage284 V boundary is not coherent across columns")
    return {
        "capture_viewport_height": viewport_height,
        "controls": controls, "u_profiles": u_profiles, "v_profiles": v_profiles,
    }


def verify(root: Path) -> dict:
    folder = Path(root) / CASE
    manifest = json.loads(file_bytes(folder / "generated-input.json"))
    masked = near_atlas()
    baseline = generated_dds((*VIOLET, 128))
    digest = hashlib.sha256(masked).hexdigest()
    baseline_digest = hashlib.sha256(baseline).hexdigest()
    if (manifest.get("schema") != SCHEMA
            or manifest.get("scenario") != CASE
            or manifest.get("changed_file") != "material0.dds"
            or manifest.get("generated_only") is not True
            or manifest.get("original_ps3_resources") is not False
            or manifest.get("actual_gpu_render_verified") is not False
            or manifest.get("near_original_dds_sha256") != baseline_digest
            or manifest.get("near_dds_sha256") != digest
            or manifest.get("near_alpha_split_u") != SPLIT_U
            or manifest.get("near_alpha_split_v") != SPLIT_V
            or manifest.get("expected_half_transition_x") != U_EXPECTED_X
            or manifest.get("expected_half_transition_y") != V_EXPECTED_Y
            or manifest.get("near_texture_dimensions") != [WIDTH, WIDTH]
            or manifest.get("u_profile_rows") != list(U_PROFILE_ROWS)
            or manifest.get("u_profile_x_positions") != list(U_PROFILE_X)
            or manifest.get("v_profile_columns") != list(V_PROFILE_COLUMNS)
            or manifest.get("v_profile_y_positions") != list(V_PROFILE_Y)
            or manifest.get("capture_viewport_height") != CAPTURE_VIEWPORT_HEIGHT
            or manifest.get("capture_viewport_probe_x") != CAPTURE_VIEWPORT_PROBE_X
            or manifest.get("control_probe_positions") != {
                key: list(value) for key, value in CONTROL_POSITIONS.items()
            }
            or manifest.get("expected_native_pass_order") != [2, 1, 0]
            or manifest.get("expected_probe_rgb") != {
                key: list(expected_at(key)) for key in CONTROL_POSITIONS
            }
            or manifest.get("profile_goal") !=
            "verify orthogonal U and V alpha edges simultaneously in one generated DDS without assuming sampler filtering"):
        raise ValueError("Stage284 generated UV-cross provenance mismatch")
    for phase in ("before", "after"):
        if file_bytes(folder / f"near-dds-{phase}.sha256") != (
                digest + "\n").encode("ascii"):
            raise ValueError("Stage284 DDS identity changed during guest run")
    if file_bytes(folder / "native-sort-pass.txt") != b"FOJ_NATIVE_SORT_V1 2,1,0\n":
        raise ValueError("Stage284 native sort receipt mismatch")
    if file_bytes(folder / "native-alpha-pass.txt") != expected_receipt("original"):
        raise ValueError("Stage284 native alpha/blend/depth receipt mismatch")
    file_bytes(folder / "guest.log")
    for marker in ("native-rear-alpha-reject.txt", "native-topology-reject.txt"):
        forbidden = folder / marker
        if forbidden.exists() or forbidden.is_symlink():
            raise ValueError("Stage284 contradictory native GPU rejection")
    first = inspect(folder / "gpu-initial.png")
    later = inspect(folder / "gpu-later.png")
    with Image.open(folder / "gpu-initial.png") as image_a, Image.open(
            folder / "gpu-later.png") as image_b:
        a, b = image_a.convert("RGB"), image_b.convert("RGB")
    if ImageChops.difference(a, b).getbbox() is None:
        raise ValueError("Stage284 duplicate framebuffer captures")
    if sum(a.getpixel(point) != b.getpixel(point) for point in BACKGROUNDS) < 3:
        raise ValueError("Stage284 GPU clear-color phase did not change")
    if first["u_profiles"] != later["u_profiles"] or first["v_profiles"] != later["v_profiles"]:
        raise ValueError("Stage284 material edge profiles changed between frames")
    sample_count = 2 * (
        len(U_PROFILE_ROWS) * len(U_PROFILE_X)
        + len(V_PROFILE_COLUMNS) * len(V_PROFILE_Y)
    )
    return {
        "schema": "foj.stage284.real_native_orthogonal_uv_alpha_edges.v1",
        "generated_only": True, "original_ps3_resources": False,
        "real_neixum_frames_required": 2, "profile_sample_count": sample_count,
        "native_pass_receipts_checked": True, "sampler_filter_mode": "NOT_INFERRED",
        "physical_switch_verified": False, "u_split_texel": SPLIT_U,
        "v_split_texel": SPLIT_V, "initial": first, "later": later,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = verify(args.evidence)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Stage284 GPU evidence refused: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
