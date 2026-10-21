#!/usr/bin/env python3
"""Stage292: synthetic GTF-like linear-BGRA -> exact classic RGBA8 DDS roundtrip.

This is NOT an original PS3 decoder. It accepts only deterministic fixtures
carrying a Stage292-only marker and matching every synthetic source byte.
No filesystem inputs, source paths, conversion of private game data, or uploads.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys

from tools.foj_gpu_local_dds_preflight import (
    MAX_WIDTH, MAX_HEIGHT, MAX_MIPS, classify_classic_dds,
)

SCHEMA = "foj.stage292.synthetic_gtf_linear_bgra_to_dds.v1"
VERSION = bytes.fromhex("02000101")
TAG = b"FOJ_STAGE292_SYNTHETIC_ONLY_V1"
HEADER_BYTES = 128
FORMAT_LINEAR_RGBA_HINT = 0xA5
MAX_SOURCE_BYTES = 128 + 393216


def _levels(width: int, height: int, mips: int) -> tuple[tuple[int, int], ...]:
    if (type(width) is not int or type(height) is not int or
            type(mips) is not int or width < 8 or width > MAX_WIDTH or
            width % 8 or height < 1 or height > MAX_HEIGHT or
            not 1 <= mips <= MAX_MIPS):
        raise ValueError("Stage292 invalid synthetic image bounds")
    result = []
    w, h = width, height
    for _ in range(mips):
        result.append((w, h))
        if w == h == 1 and len(result) < mips:
            raise ValueError("Stage292 synthetic mip count exceeds dimensions")
        w, h = max(1, w // 2), max(1, h // 2)
    return tuple(result)


def _rgba_pixel(x: int, y: int, level: int, opaque: bool) -> bytes:
    return bytes((
        (17 + 37*x + 13*y + 19*level) & 255,
        (61 + 7*x + 29*y + 5*level) & 255,
        (103 + 3*x + 11*y + 27*level) & 255,
        255 if opaque or (x+y+level) % 3 else 128,
    ))


def canonical_rgba(width: int, height: int, mips: int, opaque: bool) -> bytes:
    if type(opaque) is not bool:
        raise ValueError("Stage292 invalid alpha profile")
    result = bytearray()
    for level, (w, h) in enumerate(_levels(width, height, mips)):
        for y in range(h):
            for x in range(w):
                result.extend(_rgba_pixel(x, y, level, opaque))
    return bytes(result)


def _synthetic_header(width: int, height: int, mips: int,
                      opaque: bool, total: int) -> bytes:
    raw = bytearray(HEADER_BYTES)
    raw[:4] = VERSION
    struct.pack_into(">I", raw, 8, 1)                  # invented one-image descriptor
    struct.pack_into(">I", raw, 16, HEADER_BYTES)       # invented payload offset
    struct.pack_into(">I", raw, 20, total)              # invented byte count
    raw[36:40] = bytes((FORMAT_LINEAR_RGBA_HINT, mips, 2, 0))
    struct.pack_into(">HH", raw, 44, width, height)
    struct.pack_into(">I", raw, 48, width * 4)          # invented base pitch
    raw[56] = int(opaque)                              # invented alpha-profile byte
    raw[64:64 + len(TAG)] = TAG                        # MUST NEVER appear in game data
    return bytes(raw)


def generate_fixture(width: int = 64, height: int = 64,
                     mips: int = 1, opaque: bool = False) -> bytes:
    rgba = canonical_rgba(width, height, mips, opaque)
    bgra = bytearray(len(rgba))
    for i in range(0, len(rgba), 4):
        r, g, b, a = rgba[i:i + 4]
        bgra[i:i + 4] = bytes((b, g, r, a))
    result = _synthetic_header(width, height, mips, opaque, len(bgra)) + bytes(bgra)
    if len(result) > MAX_SOURCE_BYTES:
        raise ValueError("Stage292 synthetic source exceeds absolute byte bound")
    return result


def convert_fixture(blob: bytes) -> tuple[bytes, dict]:
    if (type(blob) is not bytes or
            not HEADER_BYTES <= len(blob) <= MAX_SOURCE_BYTES or
            blob[:4] != VERSION or blob[64:64 + len(TAG)] != TAG):
        raise ValueError("Stage292 refuses non-synthetic source")
    width, height = struct.unpack_from(">HH", blob, 44)
    mips = blob[37]
    if blob[56] not in (0, 1):
        raise ValueError("Stage292 invalid synthetic alpha profile")
    opaque = bool(blob[56])
    levels = _levels(width, height, mips)
    expected_size = sum(w * h * 4 for w, h in levels)
    if blob[:HEADER_BYTES] != _synthetic_header(
            width, height, mips, opaque, expected_size):
        raise ValueError("Stage292 invented header differs from exact fixture contract")
    # This byte-for-byte guard means actual PS3 resources can never be
    # represented as valid inputs through this function by accident.
    if blob != generate_fixture(width, height, mips, opaque):
        raise ValueError("Stage292 only accepts deterministic invented pixel data")

    bgra = blob[HEADER_BYTES:]
    rgba = bytearray(len(bgra))
    for i in range(0, len(bgra), 4):
        b, g, r, a = bgra[i:i + 4]
        rgba[i:i + 4] = bytes((r, g, b, a))
    if bytes(rgba) != canonical_rgba(width, height, mips, opaque):
        raise ValueError("Stage292 channel or alpha mapping changed")

    hdr = bytearray(HEADER_BYTES)
    hdr[:4] = b"DDS "
    has_mips = mips > 1
    for at, value in (
        (4, 124), (8, 0x100F | (0x20000 if has_mips else 0)),
        (12, height), (16, width), (20, width * 4),
        (28, mips), (76, 32), (80, 0x41), (88, 32),
        (92, 0xff), (96, 0xff00), (100, 0xff0000),
        (104, 0xff000000),
        (108, 0x401008 if has_mips else 0x1000),
    ):
        struct.pack_into("<I", hdr, at, value)
    dds = bytes(hdr) + bytes(rgba)
    classified = classify_classic_dds(dds)
    if (classified["format"] != "RGBA8" or
            classified["width"] != width or classified["height"] != height or
            classified["declared_mip_levels"] != mips or
            classified["dds_file_bytes"] != len(dds)):
        raise ValueError("Stage292 native DDS acceptance contract mismatch")
    return dds, {
        "schema": SCHEMA,
        "input_kind": "deterministic-invented-gtf-like-only",
        "source_version_is_a_format_hypothesis": True,
        "source_channel_order_is_invented_bgra": True,
        "output_format": "native-loader-compatible-RGBA8-DDS",
        "width": width, "height": height, "mip_levels": mips,
        "alpha_profile": "opaque" if opaque else "mixed",
        "output_byte_count": len(dds),
        "original_ps3_resources_processed": False,
        "original_foj_material_mapping_verified": False,
        "physical_switch_gpu_verified": False,
        "production_game_conversion_permitted": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--height", type=int, default=64)
    parser.add_argument("--mips", type=int, default=1)
    parser.add_argument("--opaque", action="store_true")
    args = parser.parse_args(argv)
    try:
        _, report = convert_fixture(generate_fixture(
            args.width, args.height, args.mips, args.opaque))
    except (ValueError, TypeError, struct.error):
        print("Stage292 synthetic-only DDS experiment refused.", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
