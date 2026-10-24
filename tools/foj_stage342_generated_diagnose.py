#!/usr/bin/env python3
"""Generated-only Stage342 GPU-failure diagnosis; never releases frame pixels."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re

from PIL import Image, ImageChops

from tools.foj_stage340_fixture import fixture_bytes, summary as fixture_summary
from tools.foj_stage342_frame_gate import (
    EVIDENCE_FILES, FRAME_HEIGHT, FRAME_WIDTH, SAMPLE_X, SAMPLE_Y,
    CHANNEL_TOLERANCE, WIDTH, HEIGHT, _marker, _regular, _sample_uv,
    decode_bgra8_dds,
)

SCHEMA = "foj.stage342.generated_only_failure_diagnostic.v1"
CANDIDATES = (
    "identity", "flip_u", "flip_v", "flip_uv",
    "swap_rb", "swap_rb_flip_u", "swap_rb_flip_v", "swap_rb_flip_uv",
)



def invert_generated_rgb(rgb: tuple[int, int, int]) -> tuple[int, int] | None:
    """Invert the public fixture's RGB map; no original-source data accepted.

    R=3x+5y+17, G=11x+7y+23, B=13x+2y+91, modulo 256.
    det([[3,5],[13,2]])=-59; inverse of -59 mod 256 is 13.
    The green channel independently validates the recovered coordinates.
    """
    r, g, b = rgb
    pr, pb = (int(r) - 17) & 255, (int(b) - 91) & 255
    x = (13 * (2 * pr - 5 * pb)) & 255
    y = (13 * (-13 * pr + 3 * pb)) & 255
    if (11 * x + 7 * y + 23) & 255 != int(g):
        return None
    return x, y


def _fit_generated_affine_texels(
    points: list[tuple[int, int, int, int]],
) -> dict | None:
    """Fit recovered generated-only texels to expected grid, aggregate only."""
    if len(points) < 9:
        return None
    matrix = [[0.0] * 3 for _ in range(3)]
    outputs = [[0.0] * 3 for _ in range(2)]
    for expected_x, expected_y, recovered_x, recovered_y in points:
        row = (float(expected_x), float(expected_y), 1.0)
        for i in range(3):
            for j in range(3):
                matrix[i][j] += row[i] * row[j]
            outputs[0][i] += row[i] * recovered_x
            outputs[1][i] += row[i] * recovered_y

    def solve(rhs: list[float]) -> list[float] | None:
        augmented = [matrix[i][:] + [rhs[i]] for i in range(3)]
        for column in range(3):
            pivot = max(range(column, 3), key=lambda i: abs(augmented[i][column]))
            if abs(augmented[pivot][column]) < 1e-9:
                return None
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
            value = augmented[column][column]
            augmented[column] = [v / value for v in augmented[column]]
            for i in range(3):
                if i == column:
                    continue
                factor = augmented[i][column]
                augmented[i] = [
                    augmented[i][k] - factor * augmented[column][k]
                    for k in range(4)
                ]
        return [augmented[i][3] for i in range(3)]

    x_map, y_map = solve(outputs[0]), solve(outputs[1])
    if x_map is None or y_map is None:
        return None
    total_squared = 0.0
    max_abs_error = 0.0
    for expected_x, expected_y, recovered_x, recovered_y in points:
        sx = sum(c * q for c, q in zip(x_map, (expected_x, expected_y, 1.0)))
        sy = sum(c * q for c, q in zip(y_map, (expected_x, expected_y, 1.0)))
        dx, dy = sx - recovered_x, sy - recovered_y
        total_squared += dx * dx + dy * dy
        max_abs_error = max(max_abs_error, abs(dx), abs(dy))
    return {
        "fit_points": len(points),
        "source_texel_x_from_expected_xy": [round(x, 4) for x in x_map],
        "source_texel_y_from_expected_xy": [round(y, 4) for y in y_map],
        "rmse_texels": round((total_squared / (2 * len(points))) ** 0.5, 4),
        "max_abs_residual_texels": round(max_abs_error, 4),
    }


def _longest_provenance_run(
    pixels, *, horizontal: bool, position: int, extent: int,
) -> list[int] | None:
    """Find quad centerline bounds using only exact generated DDS RGB colors.

    Accidental valid colors outside the quad cannot set the bounds unless
    they form a contiguous run longer than one third of the capture axis.
    The returned aggregate contains no observed color or private texture.
    """
    longest_start = -1
    longest_length = 0
    current_start = -1
    current_length = 0
    for axis_position in range(extent):
        rgb = (
            pixels[axis_position, position] if horizontal
            else pixels[position, axis_position]
        )
        valid = invert_generated_rgb(rgb) is not None
        if valid:
            if current_start < 0:
                current_start = axis_position
                current_length = 0
            current_length += 1
        else:
            if current_length > longest_length:
                longest_start, longest_length = current_start, current_length
            current_start, current_length = -1, 0
    if current_length > longest_length:
        longest_start, longest_length = current_start, current_length
    if longest_start < 0 or longest_length < extent // 3:
        return None
    return [longest_start, longest_start + longest_length - 1]


def diagnose(sd_root: Path, evidence: Path) -> dict:
    sd_root, evidence = Path(sd_root), Path(evidence)
    gpu = sd_root / "switch" / "foj" / "gpu"
    if evidence.is_symlink() or not evidence.is_dir():
        raise ValueError("Stage342 diagnosis requires a regular evidence directory")
    entries = tuple(evidence.iterdir())
    if (any(p.is_symlink() or not p.is_file() for p in entries)
            or {p.name for p in entries} != EVIDENCE_FILES):
        raise ValueError("Stage342 diagnosis evidence allowlist mismatch")
    if (gpu.is_symlink() or not gpu.is_dir()
            or any(p.is_symlink() or not p.is_file() for p in gpu.iterdir())):
        raise ValueError("Stage342 diagnosis SD directory invalid")
    allowed = {"source.dds", "foj_actor.vert.dksh", "foj_triangle.frag.dksh",
               "foj-stage342-texture-sample.txt"}
    for path in gpu.iterdir():
        if path.name not in allowed and not re.fullmatch(r"foj-boot-[0-9]{2}\.txt", path.name):
            raise ValueError("Stage342 diagnosis unexpected SD file")
    generated = fixture_bytes()
    if _regular(gpu / "source.dds", len(generated)) != generated:
        raise ValueError("Stage342 diagnosis refuses any noncanonical or original DDS")
    metadata = json.loads(_regular(evidence / "generated-source.json", 4096))
    if metadata != fixture_summary(generated):
        raise ValueError("Stage342 diagnosis refuses unverified source metadata")
    runtime = _regular(evidence / "nexium-archive.sha256", 256).decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{64}  nexium-linux-x86_64\.tar\.gz", runtime):
        raise ValueError("Stage342 diagnosis requires pinned generated-only NeXium")
    _regular(evidence / "guest.log", 2 * 1024 * 1024)
    receipt_time = _marker(sd_root).stat().st_mtime_ns
    rgba = decode_bgra8_dds(generated)

    def inspect(path: Path) -> tuple[dict, Image.Image]:
        data = _regular(path, 12 * 1024 * 1024)
        if path.stat().st_mtime_ns < receipt_time:
            raise ValueError("Stage342 diagnosis rejects a stale capture")
        with Image.open(io.BytesIO(data)) as source:
            image = source.convert("RGB")
        if image.size != (FRAME_WIDTH, FRAME_HEIGHT):
            raise ValueError("Stage342 diagnosis expects 1280x720")
        pixel = image.load()
        horizontal_bounds = _longest_provenance_run(
            pixel, horizontal=True, position=FRAME_HEIGHT // 2,
            extent=FRAME_WIDTH,
        )
        vertical_bounds = _longest_provenance_run(
            pixel, horizontal=False, position=FRAME_WIDTH // 2,
            extent=FRAME_HEIGHT,
        )
        totals = {candidate: 0 for candidate in CANDIDATES}
        alpha_hypotheses = {
            "premultiplied_black": 0,
            "source_over_clear_phase_0": 0,
            "source_over_clear_phase_1": 0,
        }
        clear_phase_colors = ((54, 31, 59), (112, 145, 110))
        sampled_triplets = []
        positions_and_rgb = []
        inverse_offsets = []
        affine_points = []
        exact_source_colors = 0
        exact_expected_texels = 0
        for y in SAMPLE_Y:
            for x in SAMPLE_X:
                u, v = _sample_uv(x, y)
                observed = pixel[x, y]
                sampled_triplets.append(observed)
                positions_and_rgb.append((u, v, observed))
                source_xy = invert_generated_rgb(observed)
                if source_xy is not None:
                    exact_source_colors += 1
                    ideal_xy = (
                        min(WIDTH - 1, max(0, int(u * WIDTH))),
                        min(HEIGHT - 1, max(0, int(v * HEIGHT))),
                    )
                    exact_expected_texels += source_xy == ideal_xy
                    dx = ((source_xy[0] - ideal_xy[0] + 128) & 255) - 128
                    dy = ((source_xy[1] - ideal_xy[1] + 128) & 255) - 128
                    inverse_offsets.append((dx, dy))
                    affine_points.append((*ideal_xy, *source_xy))
                tx0 = min(WIDTH - 1, max(0, int(u * WIDTH)))
                ty0 = min(HEIGHT - 1, max(0, int(v * HEIGHT)))
                source_offset = (ty0 * WIDTH + tx0) * 4
                alpha = rgba[source_offset + 3]
                for channel in range(3):
                    source_rgb = rgba[source_offset + channel]
                    premultiplied = (source_rgb * alpha + 127) // 255
                    alpha_hypotheses["premultiplied_black"] += (
                        abs(int(observed[channel]) - premultiplied) > CHANNEL_TOLERANCE
                    )
                    for phase, clear in enumerate(clear_phase_colors):
                        over_clear = (
                            source_rgb * alpha
                            + clear[channel] * (255 - alpha) + 127
                        ) // 255
                        alpha_hypotheses[f"source_over_clear_phase_{phase}"] += (
                            abs(int(observed[channel]) - over_clear) > CHANNEL_TOLERANCE
                        )
                for candidate in CANDIDATES:
                    flip_u = candidate.endswith("flip_u") or candidate.endswith("flip_uv")
                    flip_v = candidate.endswith("flip_v") or candidate.endswith("flip_uv")
                    tx = min(WIDTH - 1, max(0, int((1.0 - u if flip_u else u) * WIDTH)))
                    ty = min(HEIGHT - 1, max(0, int((1.0 - v if flip_v else v) * HEIGHT)))
                    start = (ty * WIDTH + tx) * 4
                    expected = rgba[start:start + 3]
                    if candidate.startswith("swap_rb"):
                        expected = (expected[2], expected[1], expected[0])
                    totals[candidate] += sum(
                        abs(int(observed[channel]) - int(expected[channel])) >
                        CHANNEL_TOLERANCE for channel in range(3)
                    )
        # RGB provenance is uniquely invertible for the canonical synthetic
        # fixture. Export only counts and one aggregate displacement mode,
        # never observed channels or individual recovered texel positions.
        offset_votes = {
            offset: inverse_offsets.count(offset)
            for offset in set(inverse_offsets)
        }
        strongest_offset = (
            min(offset_votes, key=lambda offset: (
                -offset_votes[offset], abs(offset[0]) + abs(offset[1]), offset
            )) if offset_votes else None
        )
        strongest_votes = offset_votes[strongest_offset] if strongest_offset is not None else 0
        # Diagnostic-only exhaustive search for a *constant* whole-texel
        # displacement. Source must already be the canonical generated DDS.
        # Neither capture pixels nor decoded DDS bytes enter the output JSON.
        best_shift = (len(positions_and_rgb) * 3 + 1, 1 << 40, 0, 0)
        for shift_y in range(-32, 33):
            for shift_x in range(-32, 33):
                bad, total_error = 0, 0
                for u, v, observed in positions_and_rgb:
                    tx = min(WIDTH - 1, max(0, int(u * WIDTH) + shift_x))
                    ty = min(HEIGHT - 1, max(0, int(v * HEIGHT) + shift_y))
                    offset = (ty * WIDTH + tx) * 4
                    for channel in range(3):
                        error = abs(int(observed[channel]) - rgba[offset + channel])
                        bad += error > CHANNEL_TOLERANCE
                        total_error += error
                # Prefer the smallest error, then the smallest displacement.
                key = (bad, total_error, abs(shift_x) + abs(shift_y))
                if key < (best_shift[0], best_shift[1], abs(best_shift[2]) + abs(best_shift[3])):
                    best_shift = (bad, total_error, shift_x, shift_y)
        best = min(CANDIDATES, key=lambda candidate: totals[candidate])
        return ({
            "capture_sha256": hashlib.sha256(data).hexdigest(),
            "samples_checked": len(SAMPLE_X) * len(SAMPLE_Y),
            "identity_bad_channels": totals["identity"],
            "exact_generated_fixture_rgb_matches": exact_source_colors,
            "generated_texel_affine_mapping": _fit_generated_affine_texels(affine_points),
            "exact_expected_generated_texel_matches": exact_expected_texels,
            "largest_consistent_inverse_offset_votes": strongest_votes,
            "most_common_inverse_texel_offset": (
                list(strongest_offset) if strongest_votes >= 2 else None
            ),
            "alpha_composite_hypothesis_bad_channels": alpha_hypotheses,
            "distinct_rgb_triplets_at_grid": len(set(sampled_triplets)),
            "largest_repeated_rgb_triplet_count": max(
                sampled_triplets.count(value) for value in set(sampled_triplets)
            ),
            "uniform_grid_sample": len(set(sampled_triplets)) == 1,
            "generated_quad_centerline_bounds": {
                "horizontal_xy_pixels": horizontal_bounds,
                "vertical_xy_pixels": vertical_bounds,
                "expected_horizontal_xy_pixels": [128, 1151],
                "expected_vertical_xy_pixels": [72, 647],
                "independent_of_sample_grid": True,
            },
            "best_integer_texel_offset": [best_shift[2], best_shift[3]],
            "best_integer_texel_offset_bad_channels": best_shift[0],
            "best_integer_texel_offset_total_absolute_error": best_shift[1],
            "integer_texel_search_range": [-32, 32],
            "best_diagnostic_hypothesis": best,
            "bad_channels_by_hypothesis": totals,
        }, image)

    first, image_a = inspect(evidence / "gpu-initial.png")
    second, image_b = inspect(evidence / "gpu-later.png")
    if ImageChops.difference(image_a, image_b).getbbox() is None:
        raise ValueError("Stage342 diagnosis rejects duplicate frames")
    return {
        "schema": SCHEMA,
        "generated_only": True,
        "original_ps3_assets_used": False,
        "diagnostic_only": True,
        "accepted": False,
        "native_original_texture_verified": False,
        "raw_pixel_values_exported": False,
        "tolerance": CHANNEL_TOLERANCE,
        "hypotheses_are_not_acceptance": True,
        "frame_a": first,
        "frame_b": second,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sd-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = diagnose(args.sd_root, args.evidence)
        output = args.output
        if (output.exists() or output.is_symlink()
                or not output.parent.is_dir() or output.parent.is_symlink()):
            raise ValueError("Stage342 diagnostic output must be new under a regular directory")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(output, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as dest:
            json.dump(result, dest, sort_keys=True, indent=2)
            dest.write("\n")
            dest.flush()
            os.fsync(dest.fileno())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print("STAGE342_GENERATED_FAILURE_DIAGNOSTIC_ONLY_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
