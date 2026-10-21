#!/usr/bin/env python3
"""Stage291: private, prefix-only forensic triage of possible PS3 texture files.

A GTF-looking version/header is just a candidate, never proof that an FoJ
asset or a safely convertible texture was found. Only aggregate counts leave
this process. Original inputs are not decoded, extracted, modified or uploaded.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import stat
import sys

from tools.foj_fd_bound_reader import (
    READ, NOFOLLOW, DIRECTORY, _identity, bounded_directory_names,
    open_regular_at,
)
from tools.foj_stage290_private_texture_compatibility import _check_parent_chain

SCHEMA = "foj.stage291.owner_local_ps3_texture_header_triage.v1"
PREFIX_BYTES = 128
MAX_FILES = 20000
MAX_DEPTH = 64
GTF_V1 = bytes.fromhex("02000101")
GTF_ALT = bytes.fromhex("020200ff")
RSX_HINTS = {0x85: "rgba", 0x86: "bc1", 0x87: "bc2", 0x88: "bc3"}
CATEGORIES = (
    "gtf_v1_linear_rgba_hint",
    "gtf_v1_tiled_rgba_hint",
    "gtf_v1_linear_bc1_hint",
    "gtf_v1_tiled_bc1_hint",
    "gtf_v1_linear_bc2_hint",
    "gtf_v1_tiled_bc2_hint",
    "gtf_v1_linear_bc3_hint",
    "gtf_v1_tiled_bc3_hint",
    "gtf_v1_unclassified_gpu_format_hint",
    "gtf_alt_version_header_hint",
    "gtf_inconsistent_header",
    "classic_dds_deferred_to_stage290",
    "other_image_container_not_native_dds",
    "unknown_or_non_texture",
)


def _be32(prefix: bytes, offset: int) -> int:
    return int.from_bytes(prefix[offset:offset + 4], "big")


def _be16(prefix: bytes, offset: int) -> int:
    return int.from_bytes(prefix[offset:offset + 2], "big")


def classify_prefix(prefix: bytes, file_bytes: int) -> str:
    """Conservative metadata-only hints: no pixels, GTF decode or output DDS."""
    if type(prefix) is not bytes or type(file_bytes) is not int or file_bytes < 0:
        raise ValueError("Stage291 invalid bounded prefix")
    if len(prefix) > PREFIX_BYTES or len(prefix) > file_bytes:
        raise ValueError("Stage291 contradictory prefix size")
    if prefix.startswith(b"DDS "):
        return "classic_dds_deferred_to_stage290"
    if (prefix.startswith(b"\x89PNG\r\n\x1a\n") or
            prefix.startswith(b"\xff\xd8\xff") or
            prefix.startswith(b"\xabKTX 11\xbb\r\n\x1a\n") or
            prefix.startswith(b"\xabKTX 20\xbb\r\n\x1a\n")):
        return "other_image_container_not_native_dds"

    if prefix.startswith(GTF_V1):
        # This particular v2.00.1.01 *candidate layout* has been documented
        # by community tooling. Its applicability to FoJ is UNVERIFIED.
        if len(prefix) < PREFIX_BYTES:
            return "gtf_inconsistent_header"
        count, offset, payload = (_be32(prefix, 8),
                                  _be32(prefix, 16), _be32(prefix, 20))
        gpu_format, mips, dimension, cube = prefix[36:40]
        width, height = _be16(prefix, 44), _be16(prefix, 46)
        if not (count == 1 and
                offset >= PREFIX_BYTES and offset % 16 == 0 and
                offset <= file_bytes and payload > 0 and
                payload <= file_bytes - offset and
                1 <= mips <= 16 and dimension == 2 and cube == 0 and
                1 <= width <= 16384 and 1 <= height <= 16384):
            return "gtf_inconsistent_header"
        base = gpu_format & ~0x20
        fmt = RSX_HINTS.get(base)
        if fmt is None:
            return "gtf_v1_unclassified_gpu_format_hint"
        layout = "linear" if gpu_format & 0x20 else "tiled"
        return "gtf_v1_" + layout + "_" + fmt + "_hint"

    if prefix.startswith(GTF_ALT):
        # Alternate GTF versions have distinct layouts: do not borrow the
        # v1 offsets for their texture descriptors or pretend to decode them.
        if len(prefix) < 32 or file_bytes < 32:
            return "gtf_inconsistent_header"
        count, descriptor_offset = _be32(prefix, 8), _be32(prefix, 16)
        if not (1 <= count <= 4096 and
                32 <= descriptor_offset <= file_bytes):
            return "gtf_inconsistent_header"
        return "gtf_alt_version_header_hint"

    return "unknown_or_non_texture"


def analyze(root: Path, *, max_files: int = 4096) -> dict:
    if type(max_files) is not int or not 1 <= max_files <= MAX_FILES:
        raise ValueError("Stage291 invalid file budget")
    _check_parent_chain(root)
    if not NOFOLLOW or not DIRECTORY:
        raise ValueError("Stage291 platform has no safe source traversal")

    counts: Counter[str] = Counter()
    files = 0
    directories = 0
    truncated = False

    try:
        root_fd = os.open(root, READ | NOFOLLOW | DIRECTORY)
    except OSError:
        raise ValueError("Stage291 unable to open extracted source") from None

    def visit(fd: int, depth: int) -> None:
        nonlocal files, directories, truncated
        if depth > MAX_DEPTH:
            raise ValueError("Stage291 directory depth exceeded")
        directories += 1
        if directories > MAX_FILES + 1:
            raise ValueError("Stage291 directory budget exceeded")
        before = os.fstat(fd)
        if not stat.S_ISDIR(before.st_mode):
            raise ValueError("Stage291 encountered non-directory")
        names = bounded_directory_names(fd)
        children = []
        for name in names:
            try:
                entry = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except OSError:
                raise ValueError("Stage291 source changed during scan") from None
            if stat.S_ISDIR(entry.st_mode):
                children.append((name, entry))
                continue
            if not stat.S_ISREG(entry.st_mode):
                raise ValueError("Stage291 refuses symlinks and special files")
            if files >= max_files:
                truncated = True
                return
            with open_regular_at(fd, name) as (reader, opened):
                if _identity(opened) != _identity(entry):
                    raise ValueError("Stage291 file changed before scan")
                first = reader.read(PREFIX_BYTES)
                reader.seek(0)
                replay = reader.read(PREFIX_BYTES)
                if first != replay:
                    raise ValueError("Stage291 file prefix changed")
                category = classify_prefix(first, opened.st_size)
                counts[category] += 1
            try:
                final = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except OSError:
                raise ValueError("Stage291 file changed during scan") from None
            if _identity(entry) != _identity(final):
                raise ValueError("Stage291 source replaced during scan")
            files += 1

        for name, entry in children:
            try:
                child_fd = os.open(name, READ | NOFOLLOW | DIRECTORY,
                                   dir_fd=fd)
            except OSError:
                raise ValueError("Stage291 unable to enter source directory") from None
            try:
                if _identity(entry) != _identity(os.fstat(child_fd)):
                    raise ValueError("Stage291 directory identity changed")
                visit(child_fd, depth + 1)
                if _identity(entry) != _identity(os.fstat(child_fd)):
                    raise ValueError("Stage291 source directory changed")
            finally:
                os.close(child_fd)
            try:
                final = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except OSError:
                raise ValueError("Stage291 directory replaced") from None
            if _identity(final) != _identity(entry):
                raise ValueError("Stage291 directory changed after traversal")
            if truncated:
                return
        if _identity(before) != _identity(os.fstat(fd)):
            raise ValueError("Stage291 source directory changed during traversal")
        if bounded_directory_names(fd) != names:
            raise ValueError("Stage291 source listing changed")

    try:
        root_before = os.fstat(root_fd)
        visit(root_fd, 0)
        if _identity(root_before) != _identity(os.fstat(root_fd)):
            raise ValueError("Stage291 source root mutated")
        if _identity(root_before) != _identity(root.lstat()):
            raise ValueError("Stage291 source root path replaced")
    finally:
        os.close(root_fd)

    gtf = sum(value for kind, value in counts.items()
              if kind.startswith("gtf_") and kind != "gtf_inconsistent_header")
    return {
        "schema": SCHEMA,
        "source": "owner-local-extracted-files",
        "scope": "bounded-file-start-prefixes-not-full-format-validation",
        "files_scanned": files,
        "directories_visited": directories,
        "scan_complete_within_file_limit": not truncated,
        "file_limit_reached": truncated,
        "possible_gtf_container_headers": gtf,
        "gtf_header_rejected": counts["gtf_inconsistent_header"],
        "category_counts": {name: counts[name] for name in CATEGORIES},
        "conversion_permitted": False,
        "conversion_blockers": [
            "source_layout_not_proven",
            "pixel_format_and_channel_mapping_not_proven",
            "mipmap_pitch_and_swizzle_not_proven",
            "original_foj_material_mapping_not_proven",
            "native_dds_roundtrip_not_proven",
        ],
        "no_private_paths_hashes_or_bytes_exposed": True,
        "original_ps3_texture_format_verified": False,
        "physical_switch_gpu_verified": False,
        "warning": (
            "Version/signature patterns are only untrusted clues, not FoJ "
            "texture identifications. Use Stage290 for exact classic-DDS "
            "compatibility. This stage does not convert files."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extracted-root", required=True, type=Path)
    parser.add_argument("--max-files", type=int, default=4096)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.extracted_root, max_files=args.max_files)
    except (ValueError, OSError, TypeError, KeyError):
        print("Stage291 private texture header triage refused; inspect locally.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
