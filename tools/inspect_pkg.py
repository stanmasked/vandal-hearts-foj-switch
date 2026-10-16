#!/usr/bin/env python3
"""Read-only inspection of a classic PlayStation 3/PSP PKG header.

Does not decrypt, extract, modify, or execute package contents.
Reads only header and bounded plaintext metadata unless --sha256 is requested.

Layout reference: https://www.psdevwiki.com/ps3/PKG_files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import BinaryIO

MAGIC = b"\x7fPKG"
HEADER_SIZE = 0xC0
MAX_METADATA_BYTES = 4 * 1024 * 1024
MAX_METADATA_ENTRIES = 4096
MAX_CONTENT_ID_BYTES = 0x30


class PKGError(ValueError):
    """An invalid, incomplete or unsupported input file."""


def _safe_ascii(value: bytes) -> str:
    return "".join(chr(b) if 0x20 <= b <= 0x7E else "?" for b in value)


def _stream_digest(stream: BinaryIO) -> str:
    stream.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def inspect_pkg_stream(
    stream: BinaryIO,
    actual_size: int,
    *,
    filename: str = "<stream>",
    expected_title_id: str | None = None,
    hash_file: bool = False,
) -> dict:
    """Inspect an already opened seekable file or ZIP member without extraction.

    actual_size must be the reliable byte size of this stream, not the containing
    ZIP's size. This function does not decrypt the PKG's encrypted data region.
    """
    if actual_size < HEADER_SIZE:
        raise PKGError("File is too small to contain a complete classic PKG header")
    stream.seek(0)
    header = stream.read(HEADER_SIZE)
    if len(header) < HEADER_SIZE:
        raise PKGError("Could not read a complete PKG header")
    if header[:4] != MAGIC:
        if header[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
            raise PKGError("Input looks like a ZIP archive; inspect/extract the .pkg instead")
        raise PKGError("Invalid PKG magic (expected 7F 50 4B 47)")

    (
        _magic, revision, pkg_type, metadata_offset, metadata_count,
        metadata_size, item_count, declared_size, data_offset, data_size
    ) = struct.unpack_from(">4sHHIIIIQQQ", header)
    content_id_raw = header[0x30:0x30 + MAX_CONTENT_ID_BYTES].split(b"\x00", 1)[0]
    content_id = _safe_ascii(content_id_raw)
    warnings: list[str] = []

    if revision not in (0x0000, 0x8000):
        warnings.append("Unexpected revision field")
    if pkg_type not in (1, 2):
        warnings.append("Unknown classic PKG platform type")
    if declared_size != actual_size:
        warnings.append("Declared PKG size differs from actual file size")
    if data_offset > actual_size or data_size > actual_size - min(data_offset, actual_size):
        warnings.append("Declared encrypted data region extends beyond physical file")
    if metadata_offset < 0x80 or metadata_offset > actual_size:
        warnings.append("Metadata offset is outside expected header/file range")
    if metadata_size > MAX_METADATA_BYTES or metadata_count > MAX_METADATA_ENTRIES:
        warnings.append("Metadata bounds exceed safety limits; metadata parsing skipped")
    if metadata_offset + metadata_size > actual_size:
        warnings.append("Metadata region extends beyond physical file")
    if metadata_offset + metadata_size > data_offset:
        warnings.append("Metadata region overlaps declared encrypted data region")

    metadata: list[dict] = []
    if (
        metadata_offset >= 0x80
        and metadata_offset <= actual_size
        and metadata_offset + metadata_size <= actual_size
        and metadata_size <= MAX_METADATA_BYTES
        and metadata_count <= MAX_METADATA_ENTRIES
    ):
        stream.seek(metadata_offset)
        region = stream.read(metadata_size)
        position = 0
        for index in range(metadata_count):
            if position + 8 > len(region):
                warnings.append(f"Metadata entry {index}: incomplete record header")
                break
            kind, payload_size = struct.unpack_from(">II", region, position)
            position += 8
            if payload_size > len(region) - position:
                warnings.append(f"Metadata entry {index}: payload extends beyond region")
                break
            record = {"id": kind, "size": payload_size}
            payload = region[position:position + payload_size]
            if kind in (1, 2, 3) and payload_size == 4:
                key = {1: "drm_type", 2: "content_type", 3: "package_flags"}[kind]
                record[key] = struct.unpack(">I", payload)[0]
            elif kind == 4 and payload_size == 8:
                record["metadata_package_size"] = struct.unpack(">Q", payload)[0]
            elif kind == 5 and payload_size == 4:
                # A package-builder revision/version tuple, not a title ID.
                record["builder_version_raw"] = payload.hex()
            elif kind == 6 and payload_size <= 128:
                raw_id = payload.split(b"\x00", 1)[0]
                if raw_id and all(0x20 <= b <= 0x7E for b in raw_id):
                    record["title_id"] = raw_id.decode("ascii")
            # Do not include arbitrary payloads (which may contain sensitive data).
            metadata.append(record)
            position += payload_size

    expected_match = None
    if expected_title_id:
        expected_match = expected_title_id.upper() in content_id.upper()
        if not expected_match:
            warnings.append("Expected title ID not found in header content ID")
    result = {
        "filename": filename,
        "actual_size": actual_size,
        "header": {
            "revision": f"0x{revision:04X}",
            "revision_kind": {0: "debug", 0x8000: "retail"}.get(revision, "unknown"),
            "pkg_type": pkg_type,
            "platform": {1: "PS3", 2: "PSP/PS Vita"}.get(pkg_type, "unknown"),
            "content_id": content_id,
            "metadata_offset": metadata_offset,
            "metadata_count": metadata_count,
            "metadata_size": metadata_size,
            "item_count": item_count,
            "declared_size": declared_size,
            "data_offset": data_offset,
            "data_size": data_size,
            "trailer_size": actual_size - data_offset - data_size
            if data_offset <= actual_size and data_size <= actual_size - data_offset
            else None,
        },
        "metadata": metadata,
        "checks": {
            "declared_size_matches_file": declared_size == actual_size,
            "data_region_within_file": data_offset <= actual_size
            and data_size <= actual_size - min(data_offset, actual_size),
            "expected_title_id_in_content_id": expected_match,
        },
        "warnings": warnings,
    }
    if hash_file:
        result["sha256"] = _stream_digest(stream)
    return result


def inspect_pkg(
    file_path: str | Path,
    *,
    expected_title_id: str | None = None,
    hash_file: bool = False,
) -> dict:
    path = Path(file_path)
    if not path.is_file():
        raise PKGError("File does not exist or is not a regular file")
    with path.open("rb") as stream:
        return inspect_pkg_stream(
            stream,
            path.stat().st_size,
            filename=path.name,
            expected_title_id=expected_title_id,
            hash_file=hash_file,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pkg", type=Path, help="Local, unmodified .pkg file")
    parser.add_argument("--expected-title-id", help="Optional expected ID, e.g. NPEB00148")
    parser.add_argument("--sha256", action="store_true", help="Stream file to compute SHA-256")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    args = parser.parse_args(argv)
    try:
        report = inspect_pkg(
            args.pkg, expected_title_id=args.expected_title_id, hash_file=args.sha256,
        )
    except (PKGError, OSError) as exc:
        print(f"PKG inspection error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"File: {report['filename']}")
        print(f"Size: {report['actual_size']:,} bytes")
        for field, value in report["header"].items():
            print(f"  {field}: {value}")
        print(f"Metadata records parsed: {len(report['metadata'])}")
        for entry in report["metadata"]:
            print(f"  {entry}")
        for name, value in report["checks"].items():
            print(f"Check {name}: {value}")
        if "sha256" in report:
            print(f"SHA-256: {report['sha256']}")
        for message in report["warnings"]:
            print(f"WARNING: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
