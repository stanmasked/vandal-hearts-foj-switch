#!/usr/bin/env python3
"""Generated-only Stage341 GPU-failure diagnosis; never releases frame pixels."""
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
from tools.foj_stage341_frame_gate import (
    EVIDENCE_FILES, FRAME_HEIGHT, FRAME_WIDTH, SAMPLE_X, SAMPLE_Y,
    CHANNEL_TOLERANCE, WIDTH, HEIGHT, _marker, _regular, _sample_uv,
    decode_bgra8_dds,
)

SCHEMA = "foj.stage341.generated_only_failure_diagnostic.v1"
CANDIDATES = (
    "identity", "flip_u", "flip_v", "flip_uv",
    "swap_rb", "swap_rb_flip_u", "swap_rb_flip_v", "swap_rb_flip_uv",
)


def diagnose(sd_root: Path, evidence: Path) -> dict:
    sd_root, evidence = Path(sd_root), Path(evidence)
    gpu = sd_root / "switch" / "foj" / "gpu"
    if evidence.is_symlink() or not evidence.is_dir():
        raise ValueError("Stage341 diagnosis requires a regular evidence directory")
    entries = tuple(evidence.iterdir())
    if (any(p.is_symlink() or not p.is_file() for p in entries)
            or {p.name for p in entries} != EVIDENCE_FILES):
        raise ValueError("Stage341 diagnosis evidence allowlist mismatch")
    if (gpu.is_symlink() or not gpu.is_dir()
            or any(p.is_symlink() or not p.is_file() for p in gpu.iterdir())):
        raise ValueError("Stage341 diagnosis SD directory invalid")
    allowed = {"source.dds", "foj_actor.vert.dksh", "foj_triangle.frag.dksh",
               "foj-stage341-texture-sample.txt"}
    for path in gpu.iterdir():
        if path.name not in allowed and not re.fullmatch(r"foj-boot-[0-9]{2}\.txt", path.name):
            raise ValueError("Stage341 diagnosis unexpected SD file")
    generated = fixture_bytes()
    if _regular(gpu / "source.dds", len(generated)) != generated:
        raise ValueError("Stage341 diagnosis refuses any noncanonical or original DDS")
    metadata = json.loads(_regular(evidence / "generated-source.json", 4096))
    if metadata != fixture_summary(generated):
        raise ValueError("Stage341 diagnosis refuses unverified source metadata")
    runtime = _regular(evidence / "nexium-archive.sha256", 256).decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{64}  nexium-linux-x86_64\.tar\.gz", runtime):
        raise ValueError("Stage341 diagnosis requires pinned generated-only NeXium")
    _regular(evidence / "guest.log", 2 * 1024 * 1024)
    receipt_time = _marker(sd_root).stat().st_mtime_ns
    rgba = decode_bgra8_dds(generated)

    def inspect(path: Path) -> tuple[dict, Image.Image]:
        data = _regular(path, 12 * 1024 * 1024)
        if path.stat().st_mtime_ns < receipt_time:
            raise ValueError("Stage341 diagnosis rejects a stale capture")
        with Image.open(io.BytesIO(data)) as source:
            image = source.convert("RGB")
        if image.size != (FRAME_WIDTH, FRAME_HEIGHT):
            raise ValueError("Stage341 diagnosis expects 1280x720")
        pixel = image.load()
        totals = {candidate: 0 for candidate in CANDIDATES}
        sampled_triplets = []
        positions_and_rgb = []
        for y in SAMPLE_Y:
            for x in SAMPLE_X:
                u, v = _sample_uv(x, y)
                observed = pixel[x, y]
                sampled_triplets.append(observed)
                positions_and_rgb.append((u, v, observed))
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
            "distinct_rgb_triplets_at_grid": len(set(sampled_triplets)),
            "largest_repeated_rgb_triplet_count": max(
                sampled_triplets.count(value) for value in set(sampled_triplets)
            ),
            "uniform_grid_sample": len(set(sampled_triplets)) == 1,
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
        raise ValueError("Stage341 diagnosis rejects duplicate frames")
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
            raise ValueError("Stage341 diagnostic output must be new under a regular directory")
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
    print("STAGE341_GENERATED_FAILURE_DIAGNOSTIC_ONLY_NOT_ACCEPTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
