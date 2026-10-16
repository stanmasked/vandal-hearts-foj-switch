#!/usr/bin/env python3
"""Inspect a PKG inside a raw-split ZIP (.zip.001, .zip.002, etc.).

Read-only: no reassembly on disk, extraction, decryption, or game data copying.
Segments must be consecutive byte slices of *one ordinary ZIP file*. Genuine
multi-disk/spanned ZIPs are not supported by Python's zipfile module.
"""
from __future__ import annotations

import argparse
import bisect
import io
import json
import sys
import zipfile
from pathlib import Path

from tools.inspect_pkg import PKGError, inspect_pkg_stream

MAX_ZIP_ENTRIES = 8192


class JoinedParts(io.RawIOBase):
    """Seekable virtual byte stream over several source files without copying."""

    def __init__(self, paths: list[str | Path]):
        super().__init__()
        if not paths:
            raise ValueError("At least one archive part is required")
        self.paths = [Path(path) for path in paths]
        self._files = []
        self._ends = [0]
        self._position = 0
        try:
            for path in self.paths:
                if not path.is_file():
                    raise FileNotFoundError(f"Missing archive part: {path}")
                file = path.open("rb")
                self._files.append(file)
                self._ends.append(self._ends[-1] + path.stat().st_size)
        except Exception:
            for file in self._files:
                file.close()
            raise

    @property
    def size(self) -> int:
        return self._ends[-1]

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            new = offset
        elif whence == io.SEEK_CUR:
            new = self._position + offset
        elif whence == io.SEEK_END:
            new = self.size + offset
        else:
            raise ValueError("Invalid seek mode")
        if new < 0:
            raise ValueError("Cannot seek before start of joined files")
        self._position = new
        return new

    def read(self, size: int = -1) -> bytes:
        if self.closed:
            raise ValueError("I/O operation on closed joined parts")
        remaining = max(0, self.size - self._position)
        if size is None or size < 0:
            size = remaining
        else:
            size = min(size, remaining)
        chunks = []
        while size:
            idx = bisect.bisect_right(self._ends, self._position) - 1
            if idx >= len(self._files):
                break
            count = min(size, self._ends[idx + 1] - self._position)
            handle = self._files[idx]
            handle.seek(self._position - self._ends[idx])
            data = handle.read(count)
            if not data:
                raise OSError("Archive part ended before the declared length")
            chunks.append(data)
            size -= len(data)
            self._position += len(data)
        return b"".join(chunks)

    def close(self) -> None:
        if not self.closed:
            for file in self._files:
                file.close()
        super().close()


def inspect_split_archive(
    paths: list[str | Path],
    *,
    member: str | None = None,
    expected_title_id: str | None = None,
    hash_pkg: bool = False,
    verify_crc: bool = False,
) -> dict:
    """Inspect one embedded PKG without writing either ZIP or PKG to disk."""
    with JoinedParts(paths) as joined:
        try:
            with zipfile.ZipFile(joined) as archive:
                entries = archive.infolist()
                if len(entries) > MAX_ZIP_ENTRIES:
                    raise PKGError("ZIP contains too many entries for safe inspection")
                candidates = [
                    info for info in entries
                    if not info.is_dir() and info.filename.lower().endswith(".pkg")
                ]
                if member is not None:
                    candidates = [info for info in candidates if info.filename == member]
                if not candidates:
                    raise PKGError("No matching .pkg entry found in split ZIP")
                if len(candidates) != 1:
                    raise PKGError("More than one PKG found; choose --member exactly")
                target = candidates[0]
                if target.flag_bits & 0x1:
                    raise PKGError("ZIP entry is encrypted; password-protected ZIPs unsupported")
                if target.file_size < 0xC0:
                    raise PKGError("Contained PKG is smaller than a valid header")

                # zipfile verifies CRC when the entry is fully read.
                with archive.open(target, "r") as stream:
                    pkg = inspect_pkg_stream(
                        stream,
                        target.file_size,
                        filename=target.filename,
                        expected_title_id=expected_title_id,
                        hash_file=hash_pkg,
                    )
                if verify_crc:
                    broken = archive.testzip()
                    if broken is not None:
                        raise PKGError(f"ZIP CRC mismatch: {broken}")

                return {
                    "archive": {
                        "part_count": len(paths),
                        "part_sizes": [path.stat().st_size for path in joined.paths],
                        "joined_zip_size": joined.size,
                        "entry_count": len(entries),
                        "pkg_member": target.filename,
                        "pkg_member_uncompressed_size": target.file_size,
                        "pkg_member_compressed_size": target.compress_size,
                        "pkg_member_crc32": f"{target.CRC:08x}",
                        "all_entries_crc_verified": verify_crc,
                        "pkg_member_crc_verified": hash_pkg or verify_crc,
                    },
                    "pkg": pkg,
                }
        except zipfile.BadZipFile as exc:
            raise PKGError(
                "ZIP cannot be read from these parts (wrong order, missing part, "
                "corruption, or true multi-disk ZIP): " + str(exc)
            ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path, help="Ordered .zip.001 .zip.002 ...")
    parser.add_argument("--member", help="Exact ZIP member name if multiple PKGs exist")
    parser.add_argument("--expected-title-id", default="NPEB00148")
    parser.add_argument("--sha256", action="store_true", help="Hash full PKG stream and verify its CRC")
    parser.add_argument("--verify-crc", action="store_true", help="Read all ZIP entries to verify CRCs")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args(argv)
    try:
        result = inspect_split_archive(
            args.parts,
            member=args.member,
            expected_title_id=args.expected_title_id,
            hash_pkg=args.sha256,
            verify_crc=args.verify_crc,
        )
    except (OSError, PKGError, EOFError, NotImplementedError, RuntimeError) as exc:
        print(f"Split ZIP inspection error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Split archive:", len(args.parts), "parts")
        for key, value in result["archive"].items():
            print(f"  {key}: {value}")
        print("PS3 PKG:")
        for key, value in result["pkg"]["header"].items():
            print(f"  {key}: {value}")
        print("  metadata:", result["pkg"]["metadata"])
        print("  checks:", result["pkg"]["checks"])
        for warning in result["pkg"]["warnings"]:
            print("WARNING:", warning)
        if "sha256" in result["pkg"]:
            print("PKG SHA-256:", result["pkg"]["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
