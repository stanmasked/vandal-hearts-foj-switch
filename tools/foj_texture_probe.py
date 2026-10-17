#!/usr/bin/env python3
"""Read-only, metadata-only inventory of DDS candidates in locally extracted FoJ data.

No decryption, asset extraction, game data upload or PS3 format assumptions.
Finds classic DDS header signatures at file start or inside larger binaries.
An observed signature is a *candidate*, not proof of a usable game texture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
from typing import Iterator

from tools.foj_fd_bound_reader import (
    DIRECTORY, NOFOLLOW, READ, _identity, open_regular_at,
    open_regular_beneath, bounded_directory_names,
    DEFAULT_MAX_DIR_ENTRIES, DEFAULT_MAX_DIR_NAME_BYTES,
)

HEADER_SIZE = 128
CHUNK_SIZE = 1024 * 1024
DEFAULT_MAX_FILE_BYTES = 512 * 1024 * 1024
FORMATS = {
    b"DXT1": ("BC1/DXT1", 8),
    b"DXT3": ("BC2/DXT3", 16),
    b"DXT5": ("BC3/DXT5", 16),
    b"ATI1": ("BC4/ATI1", 8),
    b"ATI2": ("BC5/ATI2", 16),
    b"BC4U": ("BC4/BC4U", 8),
    b"BC5U": ("BC5/BC5U", 16),
}


def u32(blob: bytes, start: int) -> int:
    return struct.unpack_from("<I", blob, start)[0]


def parse_dds_candidate(header: bytes, *, offset: int, file_bytes: int) -> dict | None:
    """Inspect DDS metadata only. Does not decode pixels or accept game claims."""
    if len(header) != HEADER_SIZE or header[:4] != b"DDS ":
        return None
    if u32(header, 4) != 124 or u32(header, 76) != 32:
        return None
    width, height = u32(header, 16), u32(header, 12)
    if not (1 <= width <= 16384 and 1 <= height <= 16384):
        return None
    mips = u32(header, 28) or 1
    if not 1 <= mips <= 16:
        return None

    flags, fourcc = u32(header, 80), bytes(header[84:88])
    bits_per_pixel = u32(header, 88)
    payload_start = offset + HEADER_SIZE
    if flags & 0x4:
        if fourcc == b"DX10":
            fmt, block_bytes, payload_start = "DX10/extended (unclassified)", None, payload_start + 20
        elif fourcc in FORMATS:
            fmt, block_bytes = FORMATS[fourcc]
        else:
            fmt, block_bytes = "FourCC/" + fourcc.hex(), None
        is_raw = False
    elif flags & 0x40 and bits_per_pixel in (8, 16, 24, 32):
        masks = [u32(header, pos) for pos in (92, 96, 100, 104)]
        if bits_per_pixel == 32 and masks == [0xff, 0xff00, 0xff0000, 0xff000000]:
            fmt = "RGBA8"
        elif bits_per_pixel == 32 and masks == [0xff0000, 0xff00, 0xff, 0xff000000]:
            fmt = "BGRA8"
        else:
            fmt = f"uncompressed/{bits_per_pixel}-bit (masks unclassified)"
        block_bytes, is_raw = None, True
    else:
        fmt, block_bytes, is_raw = "unknown DDS pixel format", None, False

    size_known = is_raw or block_bytes is not None
    expected = 0
    if size_known:
        w, h = width, height
        for _ in range(mips):
            if is_raw:
                level = (w * h * bits_per_pixel + 7) // 8
            else:
                level = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block_bytes
            expected += level
            w, h = max(1, w // 2), max(1, h // 2)
    remaining = file_bytes - payload_start
    if not size_known:
        payload_check = "not-computed"
    elif remaining < expected:
        payload_check = "truncated"
    elif remaining == expected:
        payload_check = "ends-at-file-boundary"
    else:
        payload_check = "additional-bytes-after-declared-mips"

    return {
        "offset": offset,
        "location": "file-start" if offset == 0 else "embedded",
        "format_candidate": fmt,
        "width": width,
        "height": height,
        "declared_mip_levels": mips,
        "declared_pitch_or_linear_size": u32(header, 20),
        "expected_payload_bytes": expected if size_known else None,
        "payload_check": payload_check,
    }


def _iter_headers_stream(stream, *, max_hits: int = 128) -> Iterator[tuple[int, bytes]]:
    """Stream candidate headers from an already opened regular-file descriptor."""
    last_offset = -1
    hits = 0
    carry = b""
    read_pos = 0
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        window = carry + chunk
        base = read_pos - len(carry)
        start = 0
        while hits < max_hits:
            at = window.find(b"DDS ", start)
            if at < 0:
                break
            if at + HEADER_SIZE > len(window):
                break  # The next chunk contains the complete candidate.
            absolute = base + at
            if absolute > last_offset:
                last_offset = absolute
                hits += 1
                yield absolute, window[at:at + HEADER_SIZE]
            start = at + 4
        if hits >= max_hits:
            return
        carry = window[-(HEADER_SIZE - 1):]
        read_pos += len(chunk)



class _HashingReader:
    """Accumulate SHA-256 over the exact bytes seen by DDS header scanning."""

    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.count = 0

    def read(self, limit: int) -> bytes:
        chunk = self.stream.read(limit)
        self.digest.update(chunk)
        self.count += len(chunk)
        return chunk


def _replay_file_hash(stream, *, size: int) -> bytes:
    """Second complete pass over the *same fd*. Never export the digest."""
    stream.seek(0)
    digest = hashlib.sha256()
    count = 0
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        count += len(chunk)
        if count > size:
            raise ValueError("DDS source grew during byte replay")
        digest.update(chunk)
    if count != size:
        raise ValueError("DDS source size changed during byte replay")
    return digest.digest()


def _verified_header_candidates(stream, *, file_bytes: int,
                                max_hits: int) -> list[tuple[int, bytes]]:
    """Collect bounded DDS headers; verify complete bytes across two reads.

    Even when the maximum header count is reached early, drain the remainder
    of the first pass before comparing against the second full-file pass.
    Both digests remain in process memory and are never written to reports.
    """
    hashed = _HashingReader(stream)
    headers = list(_iter_headers_stream(hashed, max_hits=max_hits))
    while hashed.read(CHUNK_SIZE):
        pass
    if hashed.count != file_bytes:
        raise ValueError("DDS source size changed during initial scan")
    original_digest = hashed.digest.digest()
    if _replay_file_hash(stream, size=file_bytes) != original_digest:
        raise ValueError("DDS source bytes changed between read passes")
    return headers


def iter_candidate_headers(path: Path, *, max_hits: int = 128) -> Iterator[tuple[int, bytes]]:
    """Backward-compatible scanner with no-follow final file access."""
    with open_regular_beneath(path.parent, path.name) as (stream, opened):
        headers = _verified_header_candidates(
            stream, file_bytes=opened.st_size, max_hits=max_hits)
    yield from headers


def inventory(root: Path, *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
              max_files: int = 20000, max_hits_per_file: int = 128,
              max_dir_entries: int = DEFAULT_MAX_DIR_ENTRIES,
              max_dir_name_bytes: int = DEFAULT_MAX_DIR_NAME_BYTES) -> dict:
    """Enumerate with anchored descriptors, not pathname-based os.walk.

    Known symlinks and special entries are skipped (and counted), preserving
    standalone exploratory inventory behavior. The stage-150 gate rejects
    any such skip. Changes at an open or during a directory visit fail closed.
    """
    if (type(max_file_bytes) is not int or max_file_bytes < 0 or
            type(max_files) is not int or max_files < 1 or
            type(max_hits_per_file) is not int or
            not 1 <= max_hits_per_file <= 4096):
        raise ValueError("Invalid source inventory bounds")
    if not isinstance(root, Path) or not NOFOLLOW or not DIRECTORY:
        raise ValueError("Anchored inventory requires local no-follow directories")
    if (type(max_dir_entries) is not int or not 1 <= max_dir_entries <= 100000 or
            type(max_dir_name_bytes) is not int or
            not 1 <= max_dir_name_bytes <= 64 * 1024 * 1024):
        raise ValueError("Invalid source directory listing limits")
    result: dict = {
        "schema": "foj-texture-candidates-v1",
        "source": "local-extracted-files",
        "warning": "DDS signatures are only candidates; no FoJ format verified.",
        "files_scanned": 0, "skipped_large": 0, "skipped_links": 0,
        "candidates": [], "scan_truncated_at_file_limit": False,
    }
    visited = 0
    # Opening the final root component without following a symlink keeps
    # directory identity fixed for the full traversal.
    try:
        root_fd = os.open(root, READ | NOFOLLOW | DIRECTORY)
    except OSError:
        raise ValueError("Unable to open source root safely") from None

    def _stat_child(directory_fd: int, name: str):
        try:
            return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError:
            raise ValueError("Source entry changed during enumeration") from None

    def visit(directory_fd: int, relative: str, depth: int) -> None:
        nonlocal visited
        if depth > 128:
            raise ValueError("Source directory nesting exceeds safe limit")
        start = os.fstat(directory_fd)
        if not stat.S_ISDIR(start.st_mode):
            raise ValueError("Non-directory encountered during source walk")
        visited += 1
        if visited > max_files + 1:
            raise ValueError("Too many directories for bounded DDS inventory")
        names = bounded_directory_names(
            directory_fd, max_entries=max_dir_entries,
            max_name_bytes=max_dir_name_bytes)
        # Process the files in this directory before descending into the
        # sorted children, preserving the former os.walk ordering.
        children = []
        for name in names:
            # Validate path components before touching source data.
            if not name or "/" in name or "\\" in name or name in (".", ".."):
                raise ValueError("Unsafe source directory entry")
            initial = _stat_child(directory_fd, name)
            if stat.S_ISDIR(initial.st_mode):
                children.append((name, initial))
                continue
            if not stat.S_ISREG(initial.st_mode):
                result["skipped_links"] += 1
                continue
            if result["files_scanned"] >= max_files:
                result["scan_truncated_at_file_limit"] = True
                return
            if initial.st_size > max_file_bytes:
                result["skipped_large"] += 1
                continue
            result["files_scanned"] += 1
            with open_regular_at(directory_fd, name) as (stream, opened):
                if _identity(initial) != _identity(opened):
                    raise ValueError("DDS source changed between stat and open")
                headers = _verified_header_candidates(
                    stream, file_bytes=opened.st_size,
                    max_hits=max_hits_per_file)
                for offset, head in headers:
                    metadata = parse_dds_candidate(
                        head, offset=offset, file_bytes=opened.st_size)
                    if metadata is not None:
                        metadata["relative_path"] = relative + name
                        result["candidates"].append(metadata)
            if _identity(initial) != _identity(_stat_child(directory_fd, name)):
                raise ValueError("DDS source file replaced during scan")
        for name, initial in children:
            try:
                child_fd = os.open(name, READ | NOFOLLOW | DIRECTORY,
                                   dir_fd=directory_fd)
            except OSError:
                raise ValueError("Unable to safely enter source directory") from None
            try:
                if _identity(initial) != _identity(os.fstat(child_fd)):
                    raise ValueError("Source directory replaced before open")
                visit(child_fd, relative + name + "/", depth + 1)
                if _identity(initial) != _identity(os.fstat(child_fd)):
                    raise ValueError("Source directory changed during scan")
            finally:
                os.close(child_fd)
            if _identity(initial) != _identity(_stat_child(directory_fd, name)):
                raise ValueError("Source directory path replaced during scan")
            if result["scan_truncated_at_file_limit"]:
                return
        if _identity(start) != _identity(os.fstat(directory_fd)):
            raise ValueError("Source directory changed during enumeration")
        if names != bounded_directory_names(
                directory_fd, max_entries=max_dir_entries,
                max_name_bytes=max_dir_name_bytes):
            raise ValueError("Source directory membership changed during scan")

    try:
        root_start = os.fstat(root_fd)
        visit(root_fd, "", 0)
        if _identity(root_start) != _identity(os.fstat(root_fd)):
            raise ValueError("Source root changed during enumeration")
        try:
            root_path_now = root.lstat()
        except OSError:
            raise ValueError("Source root unavailable after enumeration") from None
        if _identity(root_start) != _identity(root_path_now):
            raise ValueError("Source root path replaced during enumeration")
    finally:
        os.close(root_fd)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Locally extracted game data")
    parser.add_argument("--output", type=Path, required=True,
                        help="Local JSON report; never automatically uploaded")
    parser.add_argument("--max-file-mib", type=int, default=512)
    parser.add_argument("--max-files", type=int, default=20000)
    parser.add_argument("--max-dir-entries", type=int,
                        default=DEFAULT_MAX_DIR_ENTRIES)
    parser.add_argument("--max-dir-name-bytes", type=int,
                        default=DEFAULT_MAX_DIR_NAME_BYTES)
    args = parser.parse_args()
    if args.max_file_mib < 1 or args.max_files < 1:
        parser.error("Limits must be positive")
    try:
        report = inventory(args.directory,
                           max_file_bytes=args.max_file_mib * 1024 * 1024,
                           max_files=args.max_files,
                           max_dir_entries=args.max_dir_entries,
                           max_dir_name_bytes=args.max_dir_name_bytes)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    print(f"Scanned {report['files_scanned']} files, found "
          f"{len(report['candidates'])} possible DDS headers; "
          f"report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
