#!/usr/bin/env python3
"""Stage297: strict owner-local tile-order hypotheses vs independent RGBA digest.

Invented tile arrangements are NOT an RSX/GTF decoder or a claim about FoJ.
Never stores/prints original pixels, hashes or paths. No source-derived output.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import struct
import sys

from tools.foj_fd_bound_reader import _identity, _relative_parts, open_regular_beneath
from tools.foj_stage295_owner_local_source_integrity import _owner_digest, _pass
from tools.foj_stage290_private_texture_compatibility import _check_parent_chain
from tools.foj_stage294_owner_local_gtf_envelope import mip_shape
from tools.foj_stage296_private_rgba_layout_witness import MAX_LOCAL_FILE_BYTES
from tools.foj_gpu_local_dds_preflight import MAX_WIDTH, MAX_HEIGHT, MAX_MIPS

SCHEMA = "foj.stage297.owner_local_tile_order_dual_reference.v1"
HEADER_SIZE = 128
TILES = (4, 8)
IN_TILE_ORDERS = ("raster", "morton")
CHANNEL_ORDERS = ("rgba", "bgra")


def _morton(x: int, y: int, bits: int) -> int:
    index = 0
    for bit in range(bits):
        index |= ((x >> bit) & 1) << (bit * 2)
        index |= ((y >> bit) & 1) << (bit * 2 + 1)
    return index


def _mip_sizes(width: int, height: int, mip_count: int,
               tile: int) -> tuple[tuple[int, int, int, int], ...]:
    shapes = mip_shape(width, height, mip_count)
    return tuple((w, h, (w + tile - 1) // tile, (h + tile - 1) // tile)
                 for w, h in shapes)


def _interpret(blob: bytes, *, tile: int, in_tile: str,
               channel: str) -> tuple[bytes, int]:
    """Decode just ONE explicit invented tile hypothesis into private memory."""
    if (type(blob) is not bytes or
            not HEADER_SIZE <= len(blob) <= MAX_LOCAL_FILE_BYTES or
            type(tile) is not int or tile not in TILES or
            type(in_tile) is not str or in_tile not in IN_TILE_ORDERS or
            type(channel) is not str or channel not in CHANNEL_ORDERS):
        raise ValueError("Stage297 unsupported source or layout hypothesis")
    if blob[:4] != bytes.fromhex("02000101"):
        raise ValueError("Stage297 unsupported container version hypothesis")

    width, height = struct.unpack_from(">HH", blob, 44)
    count, offset, payload = (
        struct.unpack_from(">I", blob, 8)[0],
        struct.unpack_from(">I", blob, 16)[0],
        struct.unpack_from(">I", blob, 20)[0],
    )
    fmt, levels, dimension, cube = blob[36:40]
    pitch = struct.unpack_from(">I", blob, 48)[0]
    if (fmt != 0x85 or count != 1 or dimension != 2 or cube != 0 or
            not 8 <= width <= MAX_WIDTH or width % 8 or
            not 1 <= height <= MAX_HEIGHT or not 1 <= levels <= MAX_MIPS or
            offset != HEADER_SIZE or offset + payload != len(blob)):
        raise ValueError("Stage297 source outside bounded invented tiled layout")

    shapes = _mip_sizes(width, height, levels, tile)
    base_pitch = shapes[0][2] * tile * 4
    if pitch != base_pitch:
        raise ValueError("Stage297 base tile row pitch inconsistent")
    expected_size = sum(tx * ty * tile * tile * 4 for _, _, tx, ty in shapes)
    if payload != expected_size or len(blob) != HEADER_SIZE + expected_size:
        raise ValueError("Stage297 tile padding and mip envelope disagree")

    dst = bytearray()
    src_pos = HEADER_SIZE
    for w, h, tiles_x, tiles_y in shapes:
        level_pixels = bytearray(w * h * 4)
        level_size = tiles_x * tiles_y * tile * tile * 4
        for y in range(h):
            for x in range(w):
                block = (y // tile) * tiles_x + x // tile
                local_x, local_y = x % tile, y % tile
                if in_tile == "raster":
                    inside = local_y * tile + local_x
                else:
                    inside = _morton(local_x, local_y, tile.bit_length() - 1)
                src_offset = src_pos + (block * tile * tile + inside) * 4
                if src_offset + 4 > src_pos + level_size:
                    raise ValueError("Stage297 tile coordinate beyond mip")
                a,b,c,d = blob[src_offset:src_offset + 4]
                rgba = (a,b,c,d) if channel == "rgba" else (c,b,a,d)
                dst_offset = (y * w + x) * 4
                level_pixels[dst_offset:dst_offset+4] = bytes(rgba)
        dst.extend(level_pixels)
        src_pos += level_size
    if src_pos != len(blob):
        raise ValueError("Stage297 mip storage failed complete-range check")
    return bytes(dst), levels


def audit(source_root: Path, relative_file: str,
          source_digest_root: Path, source_digest_file: str,
          reference_digest_root: Path, reference_digest_file: str,
          *, tile: int, in_tile: str, channel: str) -> dict:
    roots = (source_root, source_digest_root, reference_digest_root)
    if any(not isinstance(root, Path) for root in roots):
        raise ValueError("Stage297 expected separate local directories")
    for root in roots:
        _check_parent_chain(root)
    resolved = [root.resolve(strict=True) for root in roots]
    if any(a == b or a in b.parents or b in a.parents
           for index,a in enumerate(resolved) for b in resolved[index+1:]):
        raise ValueError("Stage297 requires independent source and reference roots")
    _relative_parts(relative_file)
    if (type(tile) is not int or tile not in TILES or
            in_tile not in IN_TILE_ORDERS or channel not in CHANNEL_ORDERS):
        raise ValueError("Stage297 invalid explicit tile hypothesis")
    source_digest = _owner_digest(source_digest_root, source_digest_file)
    reference_digest = _owner_digest(reference_digest_root, reference_digest_file)

    with open_regular_beneath(source_root, relative_file) as (stream, source):
        if not HEADER_SIZE <= source.st_size <= MAX_LOCAL_FILE_BYTES:
            raise ValueError("Stage297 source exceeds limited local read budget")
        original = os.fstat(stream.fileno())
        first, _ = _pass(stream, source.st_size, save_prefix=False)
        stream.seek(0)
        second, _ = _pass(stream, source.st_size, save_prefix=False)
        if (not hmac.compare_digest(first, second) or
                not hmac.compare_digest(first.hex().encode("ascii"), source_digest)):
            raise ValueError("Stage297 source digest or replay mismatch")
        stream.seek(0)
        raw = stream.read(source.st_size + 1)
        if (len(raw) != source.st_size or
                not hmac.compare_digest(hashlib.sha256(raw).digest(), first) or
                _identity(original) != _identity(os.fstat(stream.fileno()))):
            raise ValueError("Stage297 third pass disagrees with owner source identity")
        rgba, levels = _interpret(raw, tile=tile, in_tile=in_tile, channel=channel)
        if not hmac.compare_digest(
                hashlib.sha256(rgba).hexdigest().encode("ascii"),
                reference_digest):
            raise ValueError("Stage297 source tile interpretation differs from reference")
    return {
        "schema": SCHEMA,
        "owner_local_source_digest_matched": True,
        "independent_private_rgba_reference_matched": True,
        "source_three_reads_consistent": True,
        "all_declared_mips_compared": True,
        "tile_size_hypothesis": tile,
        "within_tile_hypothesis": in_tile,
        "channel_order_hypothesis": channel,
        "source_hash_and_reference_hash_exposed": False,
        "source_or_decoded_pixels_exported": False,
        "original_foj_source_format_verified": False,
        "original_foj_material_mapping_verified": False,
        "original_game_texture_conversion_authorized": False,
        "original_game_gpu_verified": False,
        "physical_switch_verified": False,
        "warning": (
            "Invented raster/Morton tile ordering is not an RSX descriptor "
            "interpretation. Reference pixels must be obtained independently."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--relative-file", required=True)
    parser.add_argument("--source-digest-root", required=True, type=Path)
    parser.add_argument("--source-digest-file", required=True)
    parser.add_argument("--reference-digest-root", required=True, type=Path)
    parser.add_argument("--reference-digest-file", required=True)
    parser.add_argument("--tile", choices=TILES, required=True, type=int)
    parser.add_argument("--in-tile", choices=IN_TILE_ORDERS, required=True)
    parser.add_argument("--channel", choices=CHANNEL_ORDERS, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit(
            args.source_root, args.relative_file,
            args.source_digest_root, args.source_digest_file,
            args.reference_digest_root, args.reference_digest_file,
            tile=args.tile, in_tile=args.in_tile, channel=args.channel,
        )
    except (ValueError, OSError, TypeError, struct.error):
        print("Stage297 owner-local pixel tile reference gate refused.",
              file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
