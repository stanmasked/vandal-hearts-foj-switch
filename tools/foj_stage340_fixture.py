#!/usr/bin/env python3
"""Stage340 deterministic 256x256 BGRA8 DDS fixture; generated-only public CI."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

WIDTH = HEIGHT = 256
RGBA_BYTES = WIDTH * HEIGHT * 4
DDS_BYTES = 128 + RGBA_BYTES
SCHEMA = "foj.stage340.generated_bgra8_dds_fixture.v1"


def fixture_bytes() -> bytes:
    data = bytearray(DDS_BYTES)
    data[:4] = b"DDS "
    struct.pack_into("<I", data, 4, 124)
    struct.pack_into("<I", data, 8, 0x100F)
    struct.pack_into("<I", data, 12, HEIGHT)
    struct.pack_into("<I", data, 16, WIDTH)
    struct.pack_into("<I", data, 20, WIDTH * 4)
    struct.pack_into("<I", data, 24, 0)
    struct.pack_into("<I", data, 28, 0)
    struct.pack_into("<I", data, 76, 32)
    struct.pack_into("<I", data, 80, 0x41)
    struct.pack_into("<I", data, 84, 0)
    struct.pack_into("<I", data, 88, 32)
    struct.pack_into("<I", data, 92, 0x00FF0000)
    struct.pack_into("<I", data, 96, 0x0000FF00)
    struct.pack_into("<I", data, 100, 0x000000FF)
    struct.pack_into("<I", data, 104, 0xFF000000)
    struct.pack_into("<I", data, 108, 0x1000)
    p = 128
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r = (x * 3 + y * 5 + 17) & 255
            g = (x * 11 + y * 7 + 23) & 255
            b = (x * 13 + y * 2 + 91) & 255
            a = (x * 9 + y * 3) & 255
            data[p:p+4] = bytes((b, g, r, a))
            p += 4
    return bytes(data)


def summary(blob: bytes) -> dict:
    return {
        "schema": SCHEMA,
        "generated_only": True,
        "original_ps3_assets_used": False,
        "physical_switch_verified": False,
        "width": WIDTH,
        "height": HEIGHT,
        "format": "BGRA8",
        "dds_file_bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def create(path: Path) -> dict:
    path = Path(path)
    if path.is_symlink() or path.exists() or not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError("Stage340 fixture output must be a new file in a safe existing directory")
    blob = fixture_bytes()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(blob)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return summary(blob)


def verify(path: Path) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage340 generated DDS fixture missing or not regular")
    blob = path.read_bytes()
    expected = fixture_bytes()
    if blob != expected:
        raise ValueError("Stage340 generated DDS fixture differs from canonical bytes")
    return summary(blob)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("create", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--path", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = create(args.path) if args.action == "create" else verify(args.path)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
