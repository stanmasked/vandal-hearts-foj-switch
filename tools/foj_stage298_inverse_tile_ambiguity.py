#!/usr/bin/env python3
"""Stage298: reject ambiguous invented pixel layouts against private RGBA witness.

Byte-exact inverse reconstruction is a self-consistency invariant, *not* proof
of the correct original game format. This gate additionally requires a unique
match among EVERY supported hypothesis against an independently held RGBA
digest. No original texture or derived pixels are ever written or printed.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import itertools
import json
import os
from pathlib import Path
import struct
import sys

from tools.foj_fd_bound_reader import _identity, _relative_parts, open_regular_beneath
from tools.foj_stage295_owner_local_source_integrity import _owner_digest, _pass
from tools.foj_stage290_private_texture_compatibility import _check_parent_chain
from tools.foj_stage296_private_rgba_layout_witness import MAX_LOCAL_FILE_BYTES
from tools.foj_stage297_private_tile_reference_gate import (
    TILES, IN_TILE_ORDERS, CHANNEL_ORDERS, _morton, _mip_sizes, _interpret,
)

SCHEMA = "foj.stage298.owner_local_inverse_tile_ambiguity_gate.v1"
HEADER_SIZE = 128
HYPOTHESES = tuple(itertools.product(TILES, IN_TILE_ORDERS, CHANNEL_ORDERS))


def _inverse_reconstruct(raw: bytes, rgba: bytes, *,
                         tile: int, in_tile: str, channel: str) -> bytes:
    """Put all canonical pixels back; preserve actual source padding bytes."""
    if (type(raw) is not bytes or type(rgba) is not bytes or
            type(tile) is not int or tile not in TILES or
            in_tile not in IN_TILE_ORDERS or channel not in CHANNEL_ORDERS):
        raise ValueError("Stage298 invalid inverse-layout hypothesis")
    expected, mip_count = _interpret(raw, tile=tile, in_tile=in_tile,
                                     channel=channel)
    if len(expected) != len(rgba):
        raise ValueError("Stage298 inverse canonical RGBA size mismatch")
    width, height = struct.unpack_from(">HH", raw, 44)
    shapes = _mip_sizes(width, height, mip_count, tile)
    repaired = bytearray(raw)
    position = HEADER_SIZE
    pixel_pos = 0
    for w, h, tiles_x, tiles_y in shapes:
        level_bytes = tiles_x * tiles_y * tile * tile * 4
        for y in range(h):
            for x in range(w):
                p = pixel_pos + (y * w + x) * 4
                r,g,b,a = rgba[p:p+4]
                encoded = bytes((r,g,b,a)) if channel == "rgba" else bytes((b,g,r,a))
                block = (y // tile) * tiles_x + (x // tile)
                lx, ly = x % tile, y % tile
                if in_tile == "raster":
                    inside = ly * tile + lx
                else:
                    inside = _morton(lx, ly, tile.bit_length() - 1)
                q = position + (block * tile * tile + inside) * 4
                if q+4 > position + level_bytes:
                    raise ValueError("Stage298 source layout inverse outside mip")
                repaired[q:q+4] = encoded
        pixel_pos += w * h * 4
        position += level_bytes
    if position != len(raw) or pixel_pos != len(rgba):
        raise ValueError("Stage298 inverse mip bounds inconsistent")
    return bytes(repaired)


def evaluate(raw: bytes, expected_rgba_sha256: bytes) -> dict:
    """Safe, bounded result: never returns private RGBA bytes or digest."""
    if (type(raw) is not bytes or not HEADER_SIZE <= len(raw) <= MAX_LOCAL_FILE_BYTES
            or type(expected_rgba_sha256) is not bytes
            or len(expected_rgba_sha256) != 64
            or any(c not in b"0123456789abcdef" for c in expected_rgba_sha256)):
        raise ValueError("Stage298 invalid private source or reference digest")
    matches = []
    examined = 0
    for tile, order, channel in HYPOTHESES:
        try:
            rgba, _ = _interpret(raw, tile=tile, in_tile=order, channel=channel)
        except ValueError:
            continue
        examined += 1
        if not hmac.compare_digest(
                hashlib.sha256(rgba).hexdigest().encode("ascii"),
                expected_rgba_sha256):
            continue
        inverted = _inverse_reconstruct(
            raw, rgba, tile=tile, in_tile=order, channel=channel)
        if not hmac.compare_digest(raw, inverted):
            raise ValueError("Stage298 failed exact byte preservation in inverse")
        matches.append((tile, order, channel))
    return {
        "schema": SCHEMA,
        "candidate_hypotheses": len(HYPOTHESES),
        "structurally_eligible_hypotheses": examined,
        "independent_reference_matches": len(matches),
        "decision": (
            "unique_hypothesis" if len(matches) == 1 else
            "ambiguous_hypotheses" if len(matches) > 1 else
            "no_independent_pixel_match"),
        "unique_hypothesis": (
            {"tile": matches[0][0], "within_tile": matches[0][1],
             "channel_order": matches[0][2]} if len(matches) == 1 else None),
        "every_matching_candidate_roundtripped": True,
        "source_or_reference_digest_disclosed": False,
        "source_or_decoded_image_data_exported": False,
        "original_foj_texture_format_verified": False,
        "real_game_conversion_authorized": False,
    }


def audit(source_root: Path, relative_file: str,
          source_digest_root: Path, source_digest_file: str,
          reference_digest_root: Path, reference_digest_file: str) -> dict:
    roots = (source_root, source_digest_root, reference_digest_root)
    if any(not isinstance(root, Path) for root in roots):
        raise ValueError("Stage298 requires local roots")
    for root in roots:
        _check_parent_chain(root)
    resolved = [root.resolve(strict=True) for root in roots]
    if any(a == b or a in b.parents or b in a.parents
           for index,a in enumerate(resolved) for b in resolved[index+1:]):
        raise ValueError("Stage298 requires independent nonnested roots")
    _relative_parts(relative_file)
    private_source = _owner_digest(source_digest_root, source_digest_file)
    private_reference = _owner_digest(reference_digest_root, reference_digest_file)

    with open_regular_beneath(source_root, relative_file) as (stream, record):
        if not HEADER_SIZE <= record.st_size <= MAX_LOCAL_FILE_BYTES:
            raise ValueError("Stage298 source size outside local budget")
        initial = os.fstat(stream.fileno())
        sha_a, _ = _pass(stream, record.st_size, save_prefix=False)
        stream.seek(0)
        sha_b, _ = _pass(stream, record.st_size, save_prefix=False)
        if (not hmac.compare_digest(sha_a, sha_b) or
                not hmac.compare_digest(sha_a.hex().encode("ascii"), private_source)):
            raise ValueError("Stage298 source replay and owner digest mismatch")
        stream.seek(0)
        raw = stream.read(record.st_size + 1)
        if (len(raw) != record.st_size or
                not hmac.compare_digest(hashlib.sha256(raw).digest(), sha_a) or
                _identity(initial) != _identity(os.fstat(stream.fileno()))):
            raise ValueError("Stage298 source changed during third read")
        match = evaluate(raw, private_reference)
    if match["decision"] != "unique_hypothesis":
        raise ValueError("Stage298 refuses missing or ambiguous source layout reference")
    return {
        **match,
        "owner_local_source_hash_matched": True,
        "separate_reference_hash_matched": True,
        "three_consistent_source_reads": True,
        "original_ps3_assets_verified": False,
        "original_material_binding_verified": False,
        "physical_switch_gpu_verified": False,
        "warning": (
            "A single unique match among eight invented choices is evidence "
            "about this reference only, not proof of actual RSX swizzle, "
            "original game provenance or readiness for DDS conversion."),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--relative-file", required=True)
    parser.add_argument("--source-digest-root", required=True, type=Path)
    parser.add_argument("--source-digest-file", required=True)
    parser.add_argument("--reference-digest-root", required=True, type=Path)
    parser.add_argument("--reference-digest-file", required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(
            args.source_root, args.relative_file,
            args.source_digest_root, args.source_digest_file,
            args.reference_digest_root, args.reference_digest_file)
    except (ValueError, OSError, TypeError, struct.error):
        print("Stage298 owner-local ambiguous-layout proof refused.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
