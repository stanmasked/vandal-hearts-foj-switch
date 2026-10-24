#!/usr/bin/env python3
"""Stage338: reduce real NeXium textured framebuffer evidence to a safe aggregate."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from tools.foj_stage330_corner_patch_guest import (
    SOURCE_FILES, RECEIPT, _check_tree, _regular, audit,
)

SCHEMA = "foj.stage338.real_native_texture_frame.v1"
ALLOWLIST = {"stage338-frame-proof.json", "nexium-archive.sha256"}
ARCHIVE_RE = re.compile(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n")

def verify_and_aggregate(source: Path) -> dict:
    source = Path(source)
    _check_tree(source, SOURCE_FILES)
    bridge = source / "bridge"
    # Reopen BOTH actual guest-captured PNGs and independently re-audit them.
    fresh = audit(bridge)
    saved = json.loads(_regular(bridge / RECEIPT))
    if fresh != saved or not fresh.get("generated_only"):
        raise ValueError("Fresh GPU screenshot audit differs from saved witness")
    flags = (
        "gpu_tile_midpoint_verified",
        "horizontal_and_vertical_linear_interpolation_verified",
        "tile_texture_sampling_verified",
        "four_quadrant_contributions_verified",
        "source_remainder_texture_verified",
        "ordered_source_then_tile_sections_verified",
    )
    if any(fresh.get(f) is not True for f in flags):
        raise ValueError("Generated texture frame proof incomplete")
    if (fresh.get("real_neixium_frames_verified") != 2 or
            fresh.get("original_ps3_assets_used") is not False or
            fresh.get("user_dds_files_read") is not False or
            fresh.get("physical_switch_verified") is not False):
        raise ValueError("Source provenance or physical proof false claim")
    checksum = _regular(source / "nexium-archive.sha256")
    if not ARCHIVE_RE.fullmatch(checksum):
        raise ValueError("NeXium binary identity checksum missing")
    return {
        "schema": SCHEMA,
        "native_nro": "foj-deko3d-stage338-native-frame.nro",
        "source_texture_transfer": "Stage336 deko3d RGBA8 path, generated only",
        "generated_only": True,
        "real_neixium_frame_count": 2,
        "framebuffer_is_real_gpu_capture": True,
        "independent_stage330_pixel_oracle": True,
        "source_and_corner_tile_samplers_verified": True,
        "four_quadrant_midpoint_and_remainder_verified": True,
        "screenshots_published": False,
        "guest_log_published": False,
        "original_ps3_assets_used": False,
        "physical_switch_verified": False,
    }

def publish(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    proof = verify_and_aggregate(source)
    if output.exists() or output.is_symlink() or not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("Refusing to overwrite public evidence")
    output.mkdir(mode=0o700)
    try:
        (output / "stage338-frame-proof.json").write_text(
            json.dumps(proof, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        with (output / "nexium-archive.sha256").open("xb") as dst:
            dst.write(_regular(source / "nexium-archive.sha256"))
        _check_tree(output, ALLOWLIST)
        if json.loads(_regular(output / "stage338-frame-proof.json")) != proof:
            raise ValueError("Proof changed during export")
    except BaseException:
        shutil.rmtree(output)
        raise
    return proof

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = publish(args.source, args.output)
    except (OSError, TypeError, KeyError, ValueError, json.JSONDecodeError):
        print("Stage338 native framebuffer evidence refused.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
