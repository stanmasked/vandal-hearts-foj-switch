#!/usr/bin/env python3
"""Stage294: owner-local GTF-like source envelope checks, NO texture decoding.

A header may match a community GTF layout without being a FoJ texture.
This tool reads exactly a bounded prefix of ONE owner-selected local file,
checks declared length/pitch/mips against several explicit hypotheses and
reports only non-identifying conclusions. It NEVER writes or converts assets.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from tools.foj_fd_bound_reader import (
    NOFOLLOW, DIRECTORY, _identity, open_regular_beneath, _relative_parts,
)
from tools.foj_gpu_local_dds_preflight import (
    MAX_WIDTH, MAX_HEIGHT, MAX_MIPS, MAX_FILE_BYTES,
)
from tools.foj_stage290_private_texture_compatibility import _check_parent_chain
from tools.foj_stage291_ps3_texture_header_triage import (
    GTF_V1, GTF_ALT, PREFIX_BYTES, classify_prefix,
)
from tools.foj_stage292_synthetic_gtf_dds_roundtrip import TAG

SCHEMA = "foj.stage294.owner_local_gtf_hypothesis_envelope.v1"
MAX_SOURCE_BYTES = 512 * 1024 * 1024
READ_BYTES = PREFIX_BYTES
BLOCK_BYTES = {"bc1": 8, "bc2": 16, "bc3": 16}
NATIVE_CANDIDATES = ("rgba", "bc1", "bc3")


def _be32(data: bytes, start: int) -> int:
    return int.from_bytes(data[start:start+4], "big")


def _be16(data: bytes, start: int) -> int:
    return int.from_bytes(data[start:start+2], "big")


def mip_shape(width: int, height: int, mips: int) -> tuple[tuple[int, int], ...]:
    if (type(width) is not int or type(height) is not int or
            type(mips) is not int or not 1 <= width <= 16384 or
            not 1 <= height <= 16384 or not 1 <= mips <= 16):
        raise ValueError("Stage294 invalid hypothesized image bounds")
    shapes = []
    w, h = width, height
    for level in range(mips):
        shapes.append((w, h))
        if level + 1 < mips and w == h == 1:
            raise ValueError("Stage294 mip chain longer than possible")
        w, h = max(1, w//2), max(1, h//2)
    return tuple(shapes)


def expected_contiguous_bytes(shapes: tuple[tuple[int, int], ...],
                              format_name: str) -> int:
    if format_name not in ("rgba", *BLOCK_BYTES):
        raise ValueError("Stage294 unknown layout hypothesis")
    total = 0
    for w, h in shapes:
        if format_name == "rgba":
            level = w * h * 4
        else:
            block_size = BLOCK_BYTES[format_name]
            level = ((w + 3)//4) * ((h + 3)//4) * block_size
        total += level
        if total > MAX_SOURCE_BYTES:
            raise ValueError("Stage294 hypothesized payload beyond hard limit")
    return total


def examine(prefix: bytes, file_bytes: int) -> dict:
    """Do not return raw offsets, dimensions, fingerprints or file names."""
    if (type(prefix) is not bytes or type(file_bytes) is not int or
            not 0 <= file_bytes <= MAX_SOURCE_BYTES or
            len(prefix) != min(READ_BYTES, file_bytes)):
        raise ValueError("Stage294 invalid bounded source observation")
    category = classify_prefix(prefix, file_bytes)
    base = {
        "schema": SCHEMA,
        "source_scope": "one_owner_selected_local_file_prefix",
        "source_format_confirmed": False,
        "original_foj_material_mapping_verified": False,
        "native_dds_conversion_authorized": False,
        "original_ps3_pixels_read_or_decoded": False,
        "physical_switch_verified": False,
        "candidate_class": category,
        "hypothetical_contiguous_envelope_match": False,
        "hypothetical_base_pitch_match": False,
        "hypothetical_exact_file_extent": False,
        "native_dds_dimension_limits_match": False,
        "native_dds_format_subset_hint": False,
        "possible_mip_chain": False,
        "synthetic_fixture_marker_seen": False,
        "decision": "no_usable_source_layout_evidence",
    }
    if not category.startswith("gtf_v1_") or category == "gtf_inconsistent_header":
        return base
    # Only this single version's INFERRED layout is considered. The checks
    # below do NOT attest to actual PS3 RSX texture storage.
    if not prefix.startswith(GTF_V1) or file_bytes < READ_BYTES:
        return base
    count, offset, payload = (
        _be32(prefix, 8), _be32(prefix, 16), _be32(prefix, 20))
    fmt, mips, dimension, cube = prefix[36:40]
    w, h, pitch = _be16(prefix, 44), _be16(prefix, 46), _be32(prefix, 48)
    base["synthetic_fixture_marker_seen"] = prefix[64:64+len(TAG)] == TAG
    # Even a synthetic marker is only a diagnostic flag. It never lifts the
    # refusal to convert unknown owner-selected data.
    if (count != 1 or dimension != 2 or cube != 0 or
            offset < READ_BYTES or offset % 16 or
            offset > file_bytes or payload > file_bytes - offset):
        base["decision"] = "inconsistent_candidate_header"
        return base
    fmt_code = fmt & ~0x20
    fmt_name = {0x85: "rgba", 0x86: "bc1", 0x87: "bc2",
                0x88: "bc3"}.get(fmt_code)
    if fmt_name is None:
        base["decision"] = "unclassified_gpu_format"
        return base
    try:
        shapes = mip_shape(w, h, mips)
        expected = expected_contiguous_bytes(shapes, fmt_name)
    except ValueError:
        base["decision"] = "inconsistent_mip_or_payload_hypothesis"
        return base
    base["possible_mip_chain"] = True
    base["native_dds_dimension_limits_match"] = (
        8 <= w <= MAX_WIDTH and w % 8 == 0 and
        1 <= h <= MAX_HEIGHT and mips <= MAX_MIPS and
        (fmt_name == "rgba" or h % 4 == 0)
    )
    base["native_dds_format_subset_hint"] = fmt_name in NATIVE_CANDIDATES
    base_pitch = (w * 4 if fmt_name == "rgba" else
                  ((w+3)//4) * BLOCK_BYTES[fmt_name])
    base["hypothetical_base_pitch_match"] = pitch == base_pitch
    base["hypothetical_contiguous_envelope_match"] = payload == expected
    base["hypothetical_exact_file_extent"] = (
        offset + expected == file_bytes and payload == expected
    )
    if not fmt & 0x20:
        base["decision"] = "nonlinear_layout_unverified"
    elif fmt_name == "bc2":
        base["decision"] = "bc2_unsupported_by_native_loader"
    elif (base["native_dds_dimension_limits_match"] and
          base["native_dds_format_subset_hint"] and
          base["hypothetical_base_pitch_match"] and
          base["hypothetical_contiguous_envelope_match"] and
          base["hypothetical_exact_file_extent"]  ):
        # Intentional: a strong envelope match does not prove GTF layout.
        base["decision"] = "candidate_envelope_consistent_under_unverified_hypothesis"
    else:
        base["decision"] = "candidate_storage_envelope_unresolved"
    return base


def examine_local(root: Path, relative: str) -> dict:
    if not isinstance(root, Path):
        raise ValueError("Stage294 requires an owner-local root")
    _check_parent_chain(root)
    _relative_parts(relative)
    if not NOFOLLOW or not DIRECTORY:
        raise ValueError("Stage294 platform lacks anchored no-follow reads")
    with open_regular_beneath(root, relative) as (stream, entry):
        if not 0 <= entry.st_size <= MAX_SOURCE_BYTES:
            raise ValueError("Stage294 local file beyond hard byte limit")
        before = os.fstat(stream.fileno())
        prefix = stream.read(READ_BYTES)
        stream.seek(0)
        second = stream.read(READ_BYTES)
        after = os.fstat(stream.fileno())
        if prefix != second or _identity(before) != _identity(after):
            raise ValueError("Stage294 source changed during prefix observation")
        result = examine(prefix, entry.st_size)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path,
                        help="Owner-local directory; do not put game inputs in CI")
    parser.add_argument("--relative-file", required=True,
                        help="Single local filename under source-root")
    args = parser.parse_args(argv)
    try:
        result = examine_local(args.source_root, args.relative_file)
    except (ValueError, OSError, TypeError):
        print("Stage294 owner-local source envelope check refused.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
