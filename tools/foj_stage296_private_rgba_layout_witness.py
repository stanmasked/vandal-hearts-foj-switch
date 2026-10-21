#!/usr/bin/env python3
"""Stage296: owner-local dual-digest proof of a *hypothesized* raw pixel layout.

Reads a single local owner-selected GTF-like candidate via no-follow fd.
Requires an independent PRIVATE SHA-256 for source bytes and a separately held
PRIVATE SHA-256 for the reference canonical RGBA mip chain. Never outputs,
exports or stores decoded pixels. This is NOT a PS3 RSX/GTF decoder.
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
from tools.foj_gpu_local_dds_preflight import MAX_WIDTH, MAX_HEIGHT, MAX_MIPS

SCHEMA = "foj.stage296.owner_local_dual_reference_rgba_layout.v1"
HEADER_SIZE = 128
MAX_LOCAL_FILE_BYTES = 2 * 1024 * 1024
MODES = ("rgba", "bgra")
ALIGNMENTS = (1, 16)


def _aligned(n: int, block: int) -> int:
    return ((n + block - 1) // block) * block


def _layout(blob: bytes, order: str, row_alignment: int) -> tuple[bytes, int]:
    """Only compare a narrowly scoped version/layout *hypothesis*, no output."""
    if type(blob) is not bytes or not HEADER_SIZE <= len(blob) <= MAX_LOCAL_FILE_BYTES:
        raise ValueError("Stage296 invalid source size")
    if order not in MODES or type(row_alignment) is not int or row_alignment not in ALIGNMENTS:
        raise ValueError("Stage296 unknown explicit source layout choice")
    if blob[:4] != bytes.fromhex("02000101"):
        raise ValueError("Stage296 unsupported GTF-like source version hypothesis")
    width, height = struct.unpack_from(">HH", blob, 44)
    fmt, levels, dim, cube = blob[36:40]
    count = struct.unpack_from(">I", blob, 8)[0]
    offset, payload = struct.unpack_from(">II", blob, 16)
    pitch = struct.unpack_from(">I", blob, 48)[0]
    if (fmt != 0xA5 or count != 1 or dim != 2 or cube != 0 or
            not 8 <= width <= MAX_WIDTH or width % 8 != 0 or
            not 1 <= height <= MAX_HEIGHT or not 1 <= levels <= MAX_MIPS or
            offset != HEADER_SIZE or offset + payload != len(blob)):
        raise ValueError("Stage296 source outside explicit single-image hypothesis")

    shapes = mip_shape(width, height, levels)
    if pitch != _aligned(width * 4, row_alignment):
        raise ValueError("Stage296 base pitch differs from selected row-alignment rule")

    output = bytearray()
    position = offset
    for w, h in shapes:
        row_bytes = w * 4
        row_stride = _aligned(row_bytes, row_alignment)
        for _ in range(h):
            if position + row_stride > len(blob):
                raise ValueError("Stage296 mip row extends beyond owner source")
            raw = blob[position:position + row_bytes]
            if order == "rgba":
                output.extend(raw)
            else:
                for at in range(0, len(raw), 4):
                    b, g, r, a = raw[at:at+4]
                    output.extend((r, g, b, a))
            position += row_stride
    if (position != len(blob) or position - offset != payload or
            len(output) != sum(w*h*4 for w, h in shapes)):
        raise ValueError("Stage296 source mip-chain bounds do not match hypothesis")
    return bytes(output), levels


def audit(source_root: Path, relative_file: str,
          source_digest_root: Path, source_digest_name: str,
          reference_digest_root: Path, reference_digest_name: str,
          *, order: str, row_alignment: int) -> dict:
    roots = (source_root, source_digest_root, reference_digest_root)
    if any(not isinstance(p, Path) for p in roots):
        raise ValueError("Stage296 all paths must be local")
    for root in roots:
        _check_parent_chain(root)
    absolute = [p.resolve(strict=True) for p in roots]
    if any(a == b or a in b.parents or b in a.parents
           for n,a in enumerate(absolute) for b in absolute[n+1:]):
        raise ValueError("Stage296 independent source and digest roots required")
    _relative_parts(relative_file)
    if (type(order) is not str or order not in MODES or
            type(row_alignment) is not int or row_alignment not in ALIGNMENTS):
        raise ValueError("Stage296 selected pixel hypothesis unsupported")
    owner = _owner_digest(source_digest_root, source_digest_name)
    reference = _owner_digest(reference_digest_root, reference_digest_name)

    with open_regular_beneath(source_root, relative_file) as (reader, info):
        if not HEADER_SIZE <= info.st_size <= MAX_LOCAL_FILE_BYTES:
            raise ValueError("Stage296 source outside bounded read budget")
        original = os.fstat(reader.fileno())
        first, _ = _pass(reader, info.st_size, save_prefix=False)
        reader.seek(0)
        repeated, _ = _pass(reader, info.st_size, save_prefix=False)
        if (not hmac.compare_digest(first, repeated) or
                not hmac.compare_digest(first.hex().encode("ascii"), owner)):
            raise ValueError("Stage296 source differs from private owner digest")
        reader.seek(0)
        raw = reader.read(info.st_size + 1)
        if (len(raw) != info.st_size or
                not hmac.compare_digest(hashlib.sha256(raw).digest(), first) or
                _identity(original) != _identity(os.fstat(reader.fileno()))):
            raise ValueError("Stage296 owner source altered during layout check")
        canonical, levels = _layout(raw, order, row_alignment)
        if not hmac.compare_digest(hashlib.sha256(canonical).hexdigest().encode("ascii"),
                                   reference):
            raise ValueError("Stage296 hypothesized pixels do not match independent reference")
    return {
        "schema": SCHEMA,
        "source": "one_owner_local_digest_bound_candidate",
        "independent_private_source_digest_matched": True,
        "independent_private_rgba_reference_digest_matched": True,
        "three_source_reads_consistent": True,
        "selected_channel_hypothesis": order,
        "selected_row_alignment": row_alignment,
        "mip_chain_compared": "all-declared-levels",
        "mip_levels_matched": True,
        "pixel_reference_matched": True,
        "source_digest_or_reference_hash_exposed": False,
        "source_pixel_bytes_exported": False,
        "source_format_verified": False,
        "original_foj_material_mapping_verified": False,
        "original_ps3_resource_provenance_verified": False,
        "native_dds_conversion_authorized": False,
        "original_game_gpu_verified": False,
        "physical_switch_verified": False,
        "warning": (
            "Digest-bound pixel equality demonstrates a specified byte-layout "
            "hypothesis only. The reference must be independently obtained; "
            "it does not identify the game, establish RSX format or authorize conversion."
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
    parser.add_argument("--order", choices=MODES, required=True)
    parser.add_argument("--row-alignment", type=int, choices=ALIGNMENTS, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = audit(args.source_root, args.relative_file,
                        args.source_digest_root, args.source_digest_file,
                        args.reference_digest_root, args.reference_digest_file,
                        order=args.order, row_alignment=args.row_alignment)
    except (OSError, ValueError, TypeError, struct.error):
        print("Stage296 private RGBA reference layout gate refused.", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
