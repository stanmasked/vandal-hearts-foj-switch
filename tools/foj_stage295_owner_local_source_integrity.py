#!/usr/bin/env python3
"""Stage295: offline source-byte integrity check against an OWNER-HELD digest.

A matching caller-supplied digest proves only equality of bytes to that digest,
NOT game origin, GTF correctness or an authorized PS3 conversion. Never output
source bytes, digest, filename, dimensions, or private manifest contents.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys

from tools.foj_fd_bound_reader import (
    _identity, _relative_parts, open_regular_beneath,
)
from tools.foj_stage290_private_texture_compatibility import _check_parent_chain
from tools.foj_stage294_owner_local_gtf_envelope import (
    MAX_SOURCE_BYTES, READ_BYTES, examine,
)

SCHEMA = "foj.stage295.owner_local_source_integrity_gate.v1"
CHUNK_BYTES = 256 * 1024
DIGEST_PATTERN = re.compile(rb"[0-9a-f]{64}\n?")


def _owner_digest(digest_root: Path, digest_name: str) -> bytes:
    _check_parent_chain(digest_root)
    if len(_relative_parts(digest_name)) != 1:
        raise ValueError("Stage295 expected an independent private digest file")
    with open_regular_beneath(digest_root, digest_name) as (stream, st):
        if (st.st_size not in (64, 65) or
                stat.S_IMODE(st.st_mode) & 0o077):
            raise ValueError("Stage295 owner digest file is not private or bounded")
        data = stream.read(66)
        stream.seek(0)
        replay = stream.read(66)
        if data != replay or len(data) != st.st_size or not DIGEST_PATTERN.fullmatch(data):
            raise ValueError("Stage295 invalid or unstable owner digest")
        return data.rstrip(b"\n")


def _pass(stream, size: int, *, save_prefix: bool) -> tuple[bytes, bytes]:
    digest = hashlib.sha256()
    count = 0
    prefix = b""
    while count < size:
        chunk = stream.read(min(CHUNK_BYTES, size-count))
        if not chunk:
            raise ValueError("Stage295 source file truncated during scan")
        if save_prefix and len(prefix) < READ_BYTES:
            prefix += chunk[:READ_BYTES-len(prefix)]
        count += len(chunk)
        digest.update(chunk)
    if stream.read(1):
        raise ValueError("Stage295 source grew during scan")
    return digest.digest(), prefix


def audit(source_root: Path, relative_file: str,
          digest_root: Path, digest_name: str) -> dict:
    if not isinstance(source_root, Path) or not isinstance(digest_root, Path):
        raise ValueError("Stage295 source and digest roots must be local directories")
    _check_parent_chain(source_root)
    _check_parent_chain(digest_root)
    if source_root.resolve() == digest_root.resolve():
        raise ValueError("Stage295 digest must live outside the source directory")
    _relative_parts(relative_file)
    owner = _owner_digest(digest_root, digest_name)
    with open_regular_beneath(source_root, relative_file) as (stream, entry):
        size = entry.st_size
        if not 1 <= size <= MAX_SOURCE_BYTES:
            raise ValueError("Stage295 source exceeds restricted local-input size")
        before = os.fstat(stream.fileno())
        first, prefix = _pass(stream, size, save_prefix=True)
        stream.seek(0)
        second, _ = _pass(stream, size, save_prefix=False)
        after = os.fstat(stream.fileno())
        if (_identity(entry) != _identity(before) or
                _identity(before) != _identity(after) or
                not hmac.compare_digest(first, second) or
                not hmac.compare_digest(first.hex().encode("ascii"), owner)):
            raise ValueError("Stage295 source differs from owner digest or changed")
        envelope = examine(prefix, size)
    # No filename, original hash, file size, address, dimension or source bytes.
    return {
        "schema": SCHEMA,
        "source": "owner-local-selected-extracted-file",
        "verified_against_owner_supplied_digest": True,
        "two_full_passes_on_same_anchored_descriptor": True,
        "source_bytes_replayed_unchanged": True,
        "digest_kept_private": True,
        "source_paths_and_bytes_not_exposed": True,
        "candidate_class": envelope["candidate_class"],
        "stage294_hypothesis_decision": envelope["decision"],
        "hypothetical_exact_file_extent": envelope[
            "hypothetical_exact_file_extent"],
        "synthetic_fixture_marker_seen": envelope[
            "synthetic_fixture_marker_seen"],
        "claimed_original_game_origin_verified": False,
        "source_format_confirmed": False,
        "original_foj_material_mapping_verified": False,
        "original_ps3_pixels_decoded": False,
        "native_dds_conversion_authorized": False,
        "physical_switch_verified": False,
        "warning": (
            "The owner-held SHA-256 proves byte equality to an independently "
            "supplied digest only. It cannot establish PS3 title provenance, "
            "asset format or permission to decode game textures."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--relative-file", required=True)
    parser.add_argument("--digest-root", required=True, type=Path)
    parser.add_argument("--digest-file", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = audit(args.source_root, args.relative_file,
                        args.digest_root, args.digest_file)
    except (ValueError, OSError, TypeError):
        # Never print source filename, digest, path, bytes or exception detail.
        print("Stage295 private source identity check refused.", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
