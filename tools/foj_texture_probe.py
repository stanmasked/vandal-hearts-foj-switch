#!/usr/bin/env python3
"""Read-only, metadata-only inventory of DDS candidates in locally extracted FoJ data.

No decryption, asset extraction, game data upload or PS3 format assumptions.
Finds classic DDS header signatures at file start or inside larger binaries.
An observed signature is a *candidate*, not proof of a usable game texture.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import struct
from typing import Iterator

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

    flags, fourcc = u32(header, 80), header[84:88]
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


def iter_candidate_headers(path: Path, *, max_hits: int = 128) -> Iterator[tuple[int, bytes]]:
    """Scan a file in bounded chunks; retain header-sized overlap."""
    last_offset = -1
    hits = 0
    with path.open("rb") as stream:
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


def inventory(root: Path, *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
              max_files: int = 20000, max_hits_per_file: int = 128) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Input must be an existing non-symlink directory")
    root = root.resolve()
    result: dict = {
        "schema": "foj-texture-candidates-v1",
        "source": "local-extracted-files",
        "warning": "DDS signatures are only candidates; no FoJ format verified.",
        "files_scanned": 0, "skipped_large": 0, "skipped_links": 0,
        "candidates": [], "scan_truncated_at_file_limit": False,
    }
    for current, dirs, filenames in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(current) / d).is_symlink())
        for filename in sorted(filenames):
            path = Path(current) / filename
            try:
                file_stat = path.lstat()
            except OSError:
                continue
            if not stat.S_ISREG(file_stat.st_mode):
                result["skipped_links"] += 1
                continue
            if result["files_scanned"] >= max_files:
                result["scan_truncated_at_file_limit"] = True
                return result
            if file_stat.st_size > max_file_bytes:
                result["skipped_large"] += 1
                continue
            result["files_scanned"] += 1
            try:
                for offset, head in iter_candidate_headers(
                        path, max_hits=max_hits_per_file):
                    metadata = parse_dds_candidate(
                        head, offset=offset, file_bytes=file_stat.st_size)
                    if metadata is not None:
                        metadata["relative_path"] = path.relative_to(root).as_posix()
                        result["candidates"].append(metadata)
            except OSError:
                # Cannot prove the contents of a file we failed to read.
                result.setdefault("read_errors", 0)
                result["read_errors"] += 1
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Locally extracted game data")
    parser.add_argument("--output", type=Path, required=True,
                        help="Local JSON report; never automatically uploaded")
    parser.add_argument("--max-file-mib", type=int, default=512)
    parser.add_argument("--max-files", type=int, default=20000)
    args = parser.parse_args()
    if args.max_file_mib < 1 or args.max_files < 1:
        parser.error("Limits must be positive")
    try:
        report = inventory(args.directory,
                           max_file_bytes=args.max_file_mib * 1024 * 1024,
                           max_files=args.max_files)
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
