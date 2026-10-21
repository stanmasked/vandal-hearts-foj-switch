#!/usr/bin/env python3
"""Stage299: cross-file consensus across independently held private RGBA witnesses.

All layout choices are INVENTED research hypotheses. Three or more different
owner-selected local image inputs can collectively disambiguate eight candidate
tile/channel layouts even when none is individually decisive. Only owner-local
input; absolutely no actual PS3 files or derived pixels in public CI.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import struct
import sys

from tools.foj_fd_bound_reader import _identity, _relative_parts, open_regular_beneath
from tools.foj_stage290_private_texture_compatibility import _check_parent_chain
from tools.foj_stage295_owner_local_source_integrity import _owner_digest, _pass
from tools.foj_stage296_private_rgba_layout_witness import MAX_LOCAL_FILE_BYTES
from tools.foj_stage297_private_tile_reference_gate import _interpret
from tools.foj_stage298_inverse_tile_ambiguity import HYPOTHESES, _inverse_reconstruct

SCHEMA = "foj.stage299.owner_local_multi_witness_consensus.v1"
MANIFEST_SCHEMA = "foj.stage299.owner_local_cases.v1"
MIN_CASES = 3
MAX_CASES = 8
MAX_MANIFEST_BYTES = 8192
FIELDS = frozenset(("source", "source_digest", "reference_digest"))


def _no_duplicate_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Stage299 duplicate manifest object field")
        obj[key] = value
    return obj


def read_manifest(root: Path, name: str) -> tuple[dict, ...]:
    if not isinstance(root, Path):
        raise ValueError("Stage299 private manifest root invalid")
    _check_parent_chain(root)
    if len(_relative_parts(name)) != 1:
        raise ValueError("Stage299 private manifest must be a single file")
    with open_regular_beneath(root, name) as (f, original):
        if (not 1 <= original.st_size <= MAX_MANIFEST_BYTES or
                stat.S_IMODE(original.st_mode) & 0o077):
            raise ValueError("Stage299 private manifest must be small and owner-only")
        content = f.read(MAX_MANIFEST_BYTES + 1)
        f.seek(0)
        repeated = f.read(MAX_MANIFEST_BYTES + 1)
        if len(content) != original.st_size or content != repeated:
            raise ValueError("Stage299 private manifest changed during read")
    try:
        payload = json.loads(content, object_pairs_hook=_no_duplicate_object)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Stage299 invalid local manifest format") from None
    if (type(payload) is not dict or set(payload) != {"schema", "cases"} or
            payload["schema"] != MANIFEST_SCHEMA or
            type(payload["cases"]) is not list or
            not MIN_CASES <= len(payload["cases"]) <= MAX_CASES):
        raise ValueError("Stage299 invalid or incomplete local witness list")
    output = []
    seen_sources = set()
    for item in payload["cases"]:
        if type(item) is not dict or set(item) != FIELDS:
            raise ValueError("Stage299 invalid private case contract")
        source, owner, reference = (
            item["source"], item["source_digest"], item["reference_digest"])
        if any(type(v) is not str for v in (source, owner, reference)):
            raise ValueError("Stage299 invalid private case path types")
        _relative_parts(source)
        if len(_relative_parts(owner)) != 1 or len(_relative_parts(reference)) != 1:
            raise ValueError("Stage299 digest files must be local file names")
        if source in seen_sources:
            raise ValueError("Stage299 repeated private source within manifest")
        seen_sources.add(source)
        output.append({"source": source, "source_digest": owner,
                       "reference_digest": reference})
    if len({c["source_digest"] for c in output}) != len(output) or (
            len({c["reference_digest"] for c in output}) != len(output)):
        raise ValueError("Stage299 requires different private digest records")
    return tuple(output)


def match_mask(raw: bytes, rgba_digest: bytes) -> int:
    """Private in-memory 8-bit layout membership, not a decoded image export."""
    if (type(raw) is not bytes or
            not 128 <= len(raw) <= MAX_LOCAL_FILE_BYTES or
            type(rgba_digest) is not bytes or len(rgba_digest) != 64 or
            any(x not in b"0123456789abcdef" for x in rgba_digest)):
        raise ValueError("Stage299 invalid source or independent reference")
    matches = 0
    for index, (tile, order, channel) in enumerate(HYPOTHESES):
        try:
            rgba, _ = _interpret(raw, tile=tile, in_tile=order,
                                 channel=channel)
        except ValueError:
            continue
        if not hmac.compare_digest(
                hashlib.sha256(rgba).hexdigest().encode("ascii"), rgba_digest):
            continue
        if not hmac.compare_digest(
                raw, _inverse_reconstruct(raw, rgba, tile=tile,
                                           in_tile=order, channel=channel)):
            raise ValueError("Stage299 inverse did not preserve source bytes")
        matches |= (1 << index)
    return matches


def consensus(masks: tuple[int, ...]) -> dict:
    if (type(masks) is not tuple or
            not MIN_CASES <= len(masks) <= MAX_CASES or
            any(type(m) is not int or not 1 <= m < (1 << len(HYPOTHESES))
                for m in masks)):
        raise ValueError("Stage299 missing or invalid independent pixel witness")
    joint = (1 << len(HYPOTHESES)) - 1
    for mask in masks:
        joint &= mask
    count = joint.bit_count()
    if count != 1:
        raise ValueError("Stage299 no uniquely corroborated common layout")
    winning = joint.bit_length() - 1
    tile, in_tile, channel = HYPOTHESES[winning]
    return {
        "schema": SCHEMA,
        "independent_cases": len(masks),
        "candidate_layouts_compared_per_case": len(HYPOTHESES),
        "individually_ambiguous_witnesses": sum(m.bit_count() > 1 for m in masks),
        "each_reference_matched_at_least_one_layout": True,
        "common_layout_hypotheses": 1,
        "consensus": {
            "tile_size": tile, "within_tile_order": in_tile,
            "channel_order": channel,
        },
        "source_digest_values_exposed": False,
        "reference_digest_values_exposed": False,
        "original_or_derived_texture_bytes_exported": False,
        "original_game_resource_provenance_verified": False,
        "original_ps3_format_verified": False,
        "material_binding_verified": False,
        "conversion_authorized": False,
        "physical_switch_verified": False,
        "warning": (
            "Unique intersection among eight invented hypotheses does not "
            "establish an original FoJ or RSX texture format; independent "
            "pixel references and authentic source provenance are essential."
        ),
    }


def _read_case(source_root: Path, case: dict, source_digest_root: Path,
               reference_digest_root: Path) -> tuple[int, bytes, bytes]:
    owner = _owner_digest(source_digest_root, case["source_digest"])
    reference = _owner_digest(reference_digest_root, case["reference_digest"])
    with open_regular_beneath(source_root, case["source"]) as (stream, record):
        if not 128 <= record.st_size <= MAX_LOCAL_FILE_BYTES:
            raise ValueError("Stage299 local witness outside source budget")
        before = os.fstat(stream.fileno())
        first, _ = _pass(stream, record.st_size, save_prefix=False)
        stream.seek(0)
        second, _ = _pass(stream, record.st_size, save_prefix=False)
        if (not hmac.compare_digest(first, second) or
                not hmac.compare_digest(first.hex().encode("ascii"), owner)):
            raise ValueError("Stage299 owner source failed independent digest check")
        stream.seek(0)
        blob = stream.read(record.st_size + 1)
        if (len(blob) != record.st_size or
                not hmac.compare_digest(first, hashlib.sha256(blob).digest()) or
                _identity(before) != _identity(os.fstat(stream.fileno()))):
            raise ValueError("Stage299 source changed during anchored third read")
        mask = match_mask(blob, reference)
    if not mask:
        raise ValueError("Stage299 independent reference had no matching layout")
    return mask, first, reference


def audit(source_root: Path, source_digest_root: Path,
          reference_digest_root: Path, manifest_root: Path,
          manifest_name: str) -> dict:
    roots = (source_root, source_digest_root, reference_digest_root, manifest_root)
    if any(not isinstance(root, Path) for root in roots):
        raise ValueError("Stage299 requires independent owner-local roots")
    for root in roots:
        _check_parent_chain(root)
    resolved = [root.resolve(strict=True) for root in roots]
    if any(a == b or a in b.parents or b in a.parents
           for i,a in enumerate(resolved) for b in resolved[i+1:]):
        raise ValueError("Stage299 private source and witness roots must be separate")
    cases = read_manifest(manifest_root, manifest_name)
    masks, source_digests, refs = [], set(), set()
    for item in cases:
        mask, fingerprint, expected = _read_case(
            source_root, item, source_digest_root, reference_digest_root)
        if fingerprint in source_digests or expected in refs:
            raise ValueError("Stage299 requires distinct source and reference evidence")
        source_digests.add(fingerprint)
        refs.add(expected)
        masks.append(mask)
    return consensus(tuple(masks))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--source-digest-root", required=True, type=Path)
    parser.add_argument("--reference-digest-root", required=True, type=Path)
    parser.add_argument("--manifest-root", required=True, type=Path)
    parser.add_argument("--manifest-file", required=True)
    args = parser.parse_args(argv)
    try:
        report = audit(args.source_root, args.source_digest_root,
                       args.reference_digest_root, args.manifest_root,
                       args.manifest_file)
    except (OSError, TypeError, ValueError, struct.error, OverflowError):
        print("Stage299 owner-local multi-witness gate refused.", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
