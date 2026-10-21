#!/usr/bin/env python3
"""Stage290: owner-local, read-only DDS compatibility triage for extracted data.

Reuses the independent Stage141 DDS header scanner and the exact classic DDS
contract of the native Switch atlas loader. No PKG decryption, conversion,
game material inference, texture publishing, or original PS3 asset access in CI.
Only aggregate counters ever leave this command; paths and bytes stay local.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

from tools.foj_fd_bound_reader import _identity, open_regular_beneath
from tools.foj_gpu_local_dds_preflight import (
    MAX_FILE_BYTES, classify_classic_dds,
)
from tools.foj_texture_probe import (
    inventory, parse_dds_candidate,
)
from tools.foj_texture_relations import _safe_relative_path

SCHEMA = "foj.stage290.local_dds_loader_compatibility.v1"
FORMATS = ("RGBA8", "BGRA8", "BC1/DXT1", "BC3/DXT5")
DEFAULT_MAX_FILES = 4096
DEFAULT_MAX_FILE_MIB = 32
MAX_FILE_MIB_LIMIT = 512


def _check_parent_chain(root: Path) -> None:
    if not isinstance(root, Path):
        raise ValueError("Stage290 requires an ordinary local extracted directory")
    absolute = root.absolute()
    if any(parent.is_symlink() for parent in (absolute, *absolute.parents)):
        raise ValueError("Stage290 refuses symlinked source ancestors")
    if not root.is_dir():
        raise ValueError("Stage290 source must be an extracted directory")


def _recheck_file_start(root: Path, candidate: dict) -> dict | None:
    relative = _safe_relative_path(candidate.get("relative_path"))
    if candidate.get("offset") != 0 or candidate.get("location") != "file-start":
        raise ValueError("Stage290 invalid file-start candidate")
    with open_regular_beneath(root, relative.as_posix()) as (stream, st):
        # A classic DDS at the beginning of a large or composite file is
        # not an exact native-loader input, regardless of its header.
        if st.st_size > MAX_FILE_BYTES:
            return None
        before = os.fstat(stream.fileno())
        first = stream.read(st.st_size + 1)
        stream.seek(0)
        replay = stream.read(st.st_size + 1)
        after = os.fstat(stream.fileno())
        if (len(first) != st.st_size or len(replay) != st.st_size or
                first != replay or _identity(before) != _identity(after)):
            raise ValueError("Stage290 source bytes changed during recheck")
        current = parse_dds_candidate(
            first[:128], offset=0, file_bytes=len(first))
        described = {name: value for name, value in candidate.items()
                     if name != "relative_path"}
        if current != described:
            raise ValueError("Stage290 scanned DDS candidate changed before validation")
        try:
            layout = classify_classic_dds(first)
        except ValueError:
            return None
        # Rear alpha must be proven opaque at *every* mip, not inferred from
        # DDS metadata or from the FourCC. Compressed formats are not allowed
        # as an opaque rear until separate block-alpha parity is verified.
        rear = (layout["format"] in ("RGBA8", "BGRA8") and
                all(alpha == 255 for alpha in first[131::4]))
        return {"format": layout["format"], "opaque_rear_eligible": rear}


def analyze(root: Path, *, max_files: int = DEFAULT_MAX_FILES,
            max_file_mib: int = DEFAULT_MAX_FILE_MIB) -> dict:
    if (type(max_files) is not int or not 1 <= max_files <= 20000 or
            type(max_file_mib) is not int or
            not 1 <= max_file_mib <= MAX_FILE_MIB_LIMIT):
        raise ValueError("Stage290 invalid bounded source inventory limits")
    _check_parent_chain(root)
    scanned = inventory(
        root, max_file_bytes=max_file_mib * 1024 * 1024,
        max_files=max_files, max_hits_per_file=32,
        max_candidates=1024, max_metadata_bytes=2 * 1024 * 1024)
    if scanned["skipped_links"]:
        raise ValueError("Stage290 refuses linked or special source entries")

    formats: Counter[str] = Counter()
    file_starts = 0
    embedded = 0
    incompatible = 0
    rear_opaque = 0
    seen_file_start = set()
    for item in scanned["candidates"]:
        if type(item) is not dict:
            raise ValueError("Stage290 invalid DDS candidate metadata")
        offset = item.get("offset")
        if type(offset) is not int or offset < 0:
            raise ValueError("Stage290 invalid candidate offset")
        if offset:
            if item.get("location") != "embedded":
                raise ValueError("Stage290 contradictory embedded DDS metadata")
            embedded += 1
            continue
        file_starts += 1
        relative = str(_safe_relative_path(item.get("relative_path")))
        if relative in seen_file_start:
            raise ValueError("Stage290 duplicate file-start DDS record")
        seen_file_start.add(relative)
        verified = _recheck_file_start(root, item)
        if verified is None:
            incompatible += 1
        else:
            if verified["format"] not in FORMATS:
                raise ValueError("Stage290 unsupported accepted native format")
            formats[verified["format"]] += 1
            rear_opaque += int(verified["opaque_rear_eligible"])

    compatible = sum(formats.values())
    if file_starts != compatible + incompatible:
        raise ValueError("Stage290 internal native DDS count mismatch")

    complete = (not scanned["scan_truncated_at_file_limit"] and
                scanned["skipped_large"] == 0)
    return {
        "schema": SCHEMA,
        "source": "owner-local-extracted-files",
        "scope": "DDS-signature-candidates-only",
        "files_scanned": scanned["files_scanned"],
        "scan_complete_within_declared_limits": complete,
        "skipped_large_files": scanned["skipped_large"],
        "file_limit_reached": scanned["scan_truncated_at_file_limit"],
        "dds_headers_seen": file_starts + embedded,
        "file_start_dds_candidates": file_starts,
        "embedded_dds_headers_not_native_inputs": embedded,
        "exact_native_dds_compatible": compatible,
        "exact_native_dds_incompatible": incompatible,
        "native_format_counts": {name: formats[name] for name in FORMATS},
        "opaque_rear_compatible_candidates": rear_opaque,
        "no_source_paths_or_fingerprints_exposed": True,
        "original_ps3_format_verified": False,
        "original_material_mapping_verified": False,
        "original_game_ready_to_render": False,
        "physical_switch_verified": False,
        "warning": (
            "Header candidates are not proven original FoJ textures. "
            "A compatible file does not imply correct materials or gameplay; "
            "PKG decryption and PS3-specific decoding are out of scope."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extracted-root", required=True, type=Path,
                        help="Owner-local directory of already extracted files; NEVER public CI")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-file-mib", type=int, default=DEFAULT_MAX_FILE_MIB)
    args = parser.parse_args(argv)
    try:
        report = analyze(args.extracted_root, max_files=args.max_files,
                         max_file_mib=args.max_file_mib)
    except (OSError, ValueError, TypeError, KeyError):
        # Do not reveal filenames, paths, exception values or user bytes.
        print("Stage290 local texture compatibility check refused; review input locally.",
              file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
