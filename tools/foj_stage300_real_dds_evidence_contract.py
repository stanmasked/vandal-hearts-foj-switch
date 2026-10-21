#!/usr/bin/env python3
"""Stage300: synthetic DDS sizes/formats matching *documented* FoJ samples.

Historical real-game DDS signatures are recorded in
docs/REAL_RESOURCE_SIGNATURES.md, October 16 2026. These are NOT the actual
game files and no original asset is loaded or reconstructed. This code only
tests whether the current strict Switch atlas DDS contract is compatible
with exactly described synthetic representations of those source envelopes.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import struct

from tools.foj_gpu_local_dds_preflight import classify_classic_dds, MAX_WIDTH

SCHEMA = "foj.stage300.documented_real_dds_envelopes_synthetic_contract.v1"


@dataclass(frozen=True)
class DocumentedEnvelope:
    name: str
    width: int
    height: int
    format: str
    bytes: int


# Metadata copied from the already published October 16 observed-source
# report. No source pixels, package bytes, hashes, or extracted paths.
HISTORICAL = (
    DocumentedEnvelope("archery_target.tga", 256, 256, "BGRA8", 262272),
    DocumentedEnvelope("avatar_flame_texture.tga", 256, 256, "BGRA8", 262272),
    DocumentedEnvelope("avatar_texture.tga", 1024, 1024, "BC1/DXT1", 524416),
    DocumentedEnvelope("balastradian_trooper_texture.tga", 256, 256, "BC1/DXT1", 32896),
    DocumentedEnvelope("bandit_lt_texture.tga", 256, 256, "BC1/DXT1", 32896),
)


def synthetic_from_envelope(e: DocumentedEnvelope) -> bytes:
    """Build test-only color blocks, NEVER extracted/publisher texture data."""
    if (type(e) is not DocumentedEnvelope or
            type(e.width) is not int or type(e.height) is not int or
            not 1 <= e.width <= 4096 or not 1 <= e.height <= 4096 or
            e.format not in ("BGRA8", "BC1/DXT1")):
        raise ValueError("Stage300 unsupported synthetic source envelope")
    h = bytearray(128)
    h[:4] = b"DDS "
    fields = [(4, 124), (12, e.height), (16, e.width), (28, 1),
              (76, 32), (108, 0x1000)]
    if e.format == "BGRA8":
        payload = bytearray()
        for y in range(e.height):
            for x in range(e.width):
                payload.extend(((x*7+y*3)&255,(x*11+y*13)&255,
                                (x*17+y*19)&255,255 if (x+y)%3 else 96))
        fields.extend(((8, 0x100f), (20, e.width * 4),
                       (80, 0x41), (88, 32),
                       (92, 0x00ff0000), (96, 0x0000ff00),
                       (100, 0x000000ff), (104, 0xff000000)))
    else:
        if e.width % 4 or e.height % 4:
            raise ValueError("Stage300 BC1 synthetic dimensions must be divisible by 4")
        blocks = (e.width//4)*(e.height//4)
        # Invented colored BC1 palette: red 565 + blue 565, changing
        # all four indices in each physical block.
        sample = struct.pack("<HHI", 0xf800, 0x001f, 0xe4e4e4e4)
        payload = sample * blocks
        fields.extend(((8, 0x81007), (20, len(payload)),
                       (80, 4), (84, 0x31545844)))
    for at, value in fields:
        struct.pack_into("<I", h, at, value)
    result = bytes(h) + bytes(payload)
    if len(result) != e.bytes:
        raise ValueError("Stage300 generated size differs from historical published evidence")
    return result


def classify_reconciliation() -> dict:
    rows = []
    for e in HISTORICAL:
        blob = synthetic_from_envelope(e)
        eligible = True
        try:
            desc = classify_classic_dds(blob)
            if (desc["format"], desc["width"], desc["height"],
                    desc["dds_file_bytes"]) != (
                    e.format, e.width, e.height, e.bytes):
                raise ValueError("Stage300 contract incorrectly classified generated envelope")
        except ValueError:
            eligible = False
        if e.width > MAX_WIDTH:
            if eligible:
                raise ValueError("Stage300 native GPU admitted an over-limit dimension")
            reason = "native_atlas_max_width_256"
        elif eligible:
            reason = "synthetic_canonical_header_accepted_not_source_verified"
        else:
            reason = "synthetic_header_rejected_for_other_reason"
        rows.append({
            "documented_name": e.name,
            "documented_format": e.format,
            "documented_width": e.width,
            "documented_height": e.height,
            "documented_bytes": e.bytes,
            "invented_matching_envelope_accepted_by_native_header": eligible,
            "native_compatibility_note": reason,
            "original_source_header_exact_native_acceptance_checked": False,
        })
    return {
        "schema": SCHEMA,
        "historical_source_reference": "docs/REAL_RESOURCE_SIGNATURES.md",
        "historical_observations_inherited_not_repeated": True,
        "synthetic_envelopes_tested": len(rows),
        "native_atlas_dimension_format_envelope_eligible": sum(
            row["invented_matching_envelope_accepted_by_native_header"] for row in rows),
        "native_atlas_dimension_format_envelope_blocked": sum(
            not row["invented_matching_envelope_accepted_by_native_header"] for row in rows),
        "real_source_bytes_reexamined_in_stage300": False,
        "actual_source_headers_accepted_by_native_gpu_proven": False,
        "native_texture_gpu_rendering_of_original_foj_content_proven": False,
        "physical_switch_tested": False,
        "source_files": rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(classify_reconciliation(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
