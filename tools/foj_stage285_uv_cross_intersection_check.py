"""Stage285 auditor for the 2-D intersection of Stage284's U/V alpha edges."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image
from tools.foj_stage280_shifted_boundary_sd import target_rgb
from tools.foj_stage284_uv_cross_sd import CASE, U_EXPECTED_X, V_EXPECTED_Y
from tools.foj_stage284_uv_cross_check import verify as verify_stage284

# A 17x17 neighborhood keeps the exact crossing and eight pixels of context
# on every side. Stage284 independently validates viewport and one-dimensional
# source-over profiles before this two-dimensional audit is accepted.
RADIUS = 8
X_MIN, X_MAX = U_EXPECTED_X - RADIUS, U_EXPECTED_X + RADIUS
Y_MIN, Y_MAX = V_EXPECTED_Y - RADIUS, V_EXPECTED_Y + RADIUS
CLEAR_RGB = target_rgb(0)
OPAQUE_RGB = target_rgb(255)
SCHEMA = "foj.stage285.real_native_uv_cross_intersection.v1"


def inspect_intersection(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage285 real guest capture missing or linked")
    with Image.open(path) as source:
        image = source.convert("RGB")
    if image.size != (1280, 720):
        raise ValueError("Stage285 unexpected capture dimensions")

    grid = []
    counts = {"northwest_clear": 0, "northeast_clear": 0,
              "southwest_clear": 0, "southeast_opaque": 0}
    for y in range(Y_MIN, Y_MAX + 1):
        row = []
        for x in range(X_MIN, X_MAX + 1):
            observed = image.getpixel((x, y))
            opaque = x >= U_EXPECTED_X and y >= V_EXPECTED_Y
            expected = OPAQUE_RGB if opaque else CLEAR_RGB
            if observed != expected:
                raise ValueError(
                    f"Stage285 intersection mismatch at ({x},{y}): "
                    f"observed={observed}, expected={expected}"
                )
            if x < U_EXPECTED_X and y < V_EXPECTED_Y:
                counts["northwest_clear"] += 1
            elif x >= U_EXPECTED_X and y < V_EXPECTED_Y:
                counts["northeast_clear"] += 1
            elif x < U_EXPECTED_X and y >= V_EXPECTED_Y:
                counts["southwest_clear"] += 1
            else:
                counts["southeast_opaque"] += 1
            row.append(observed)
        grid.append(row)

    expected_counts = {
        "northwest_clear": 64,
        "northeast_clear": 72,
        "southwest_clear": 72,
        "southeast_opaque": 81,
    }
    if counts != expected_counts:
        raise ValueError("Stage285 four-quadrant sample counts mismatch")
    packed = bytes(channel for row in grid for rgb in row for channel in rgb)
    return {
        "capture": path.name,
        "sample_count": len(grid) * len(grid[0]),
        "grid_dimensions": [len(grid[0]), len(grid)],
        "grid_sha256": hashlib.sha256(packed).hexdigest(),
        "quadrant_sample_counts": counts,
        "clear_rgb": list(CLEAR_RGB),
        "opaque_rgb": list(OPAQUE_RGB),
        "corner_checks": {
            "before_u_before_v": list(image.getpixel((U_EXPECTED_X - 1, V_EXPECTED_Y - 1))),
            "at_u_before_v": list(image.getpixel((U_EXPECTED_X, V_EXPECTED_Y - 1))),
            "before_u_at_v": list(image.getpixel((U_EXPECTED_X - 1, V_EXPECTED_Y))),
            "at_u_at_v": list(image.getpixel((U_EXPECTED_X, V_EXPECTED_Y))),
        },
    }


def verify(root: Path) -> dict:
    # Stage284 must pass first: source DDS identity, viewport, 1-D profiles,
    # real distinct guest frames and native sort/blend/depth receipts.
    stage284 = verify_stage284(root)
    if stage284.get("generated_only") is not True or stage284.get("original_ps3_resources") is not False:
        raise ValueError("Stage285 refuses non-generated or original-resource evidence")

    folder = Path(root) / CASE
    first = inspect_intersection(folder / "gpu-initial.png")
    later = inspect_intersection(folder / "gpu-later.png")
    if first["grid_sha256"] != later["grid_sha256"]:
        raise ValueError("Stage285 intersection patch changed between guest frames")
    expected_corners = {
        "before_u_before_v": list(CLEAR_RGB),
        "at_u_before_v": list(CLEAR_RGB),
        "before_u_at_v": list(CLEAR_RGB),
        "at_u_at_v": list(OPAQUE_RGB),
    }
    if first["corner_checks"] != expected_corners or later["corner_checks"] != expected_corners:
        raise ValueError("Stage285 four-corner intersection contract mismatch")

    return {
        "schema": SCHEMA,
        "generated_only": True,
        "original_ps3_resources": False,
        "physical_switch_verified": False,
        "stage284_prerequisites_passed": True,
        "sampler_filter_mode": "NOT_INFERRED",
        "crossing_x": U_EXPECTED_X,
        "crossing_y": V_EXPECTED_Y,
        "radius_pixels": RADIUS,
        "grid_dimensions": [2 * RADIUS + 1, 2 * RADIUS + 1],
        "samples_per_frame": first["sample_count"],
        "total_samples": first["sample_count"] * 2,
        "frames": [first, later],
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
        print("Stage285 GPU evidence refused: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
