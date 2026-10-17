#!/usr/bin/env python3
"""Private, read-only preflight of two classic DDS inputs for the Switch GPU demo.

This checks the exact header, mip-chain and byte-length restrictions of
gpu/atlas_dds.c. It does NOT decompress textures, convert PS3 assets, infer
game materials or establish console rendering. No source paths, hashes,
pixels or private bytes enter the JSON report.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import struct
from typing import Any

from tools.foj_fd_bound_reader import (
    READ, NOFOLLOW, DIRECTORY, _identity, open_regular_at,
)

DDS_HEADER_BYTES = 128
MAX_WIDTH = 256
MAX_HEIGHT = 256
MAX_MIPS = 9
MAX_OUTPUT_BYTES = MAX_WIDTH * MAX_HEIGHT * 4
MAX_INPUT_BYTES = MAX_OUTPUT_BYTES + MAX_OUTPUT_BYTES // 2
MAX_FILE_BYTES = DDS_HEADER_BYTES + MAX_INPUT_BYTES
SLOTS = ("material0.dds", "material1.dds")


def _u32(data: bytes, pos: int) -> int:
    return struct.unpack_from("<I", data, pos)[0]


def classify_classic_dds(blob: bytes) -> dict[str, Any]:
    """Match the acceptance contract of foj_atlas_dds_decode (not decode).

    Rejects all extended DDS, arrays, cube textures, unusual PS3 layouts,
    unsupported FourCC types, partial chains and trailing bytes.
    """
    if not isinstance(blob, bytes) or not DDS_HEADER_BYTES <= len(blob) <= MAX_FILE_BYTES:
        raise ValueError("Local DDS is outside the native GPU intake contract")
    if (blob[:4] != b"DDS " or _u32(blob, 4) != 124 or
            _u32(blob, 76) != 32 or
            any(_u32(blob, pos) for pos in (112, 116, 120, 124))):
        raise ValueError("Local DDS is outside the native GPU intake contract")

    width, height = _u32(blob, 16), _u32(blob, 12)
    if (width < 8 or width > MAX_WIDTH or width % 8 or
            height < 1 or height > MAX_HEIGHT or _u32(blob, 24)):
        raise ValueError("Local DDS is outside the native GPU intake contract")
    raw_mips = _u32(blob, 28)
    mip_count = raw_mips or 1
    possible = 1
    w, h = width, height
    while w > 1 or h > 1:
        w = max(1, w // 2)
        h = max(1, h // 2)
        possible += 1
    if mip_count > MAX_MIPS or mip_count > possible:
        raise ValueError("Local DDS is outside the native GPU intake contract")
    mip_flag = mip_count > 1
    if _u32(blob, 108) != (0x401008 if mip_flag else 0x1000):
        raise ValueError("Local DDS is outside the native GPU intake contract")

    pixel_flags, fourcc = _u32(blob, 80), _u32(blob, 84)
    raw32 = pixel_flags == 0x41 and fourcc == 0
    bc1 = pixel_flags == 4 and fourcc == 0x31545844
    bc3 = pixel_flags == 4 and fourcc == 0x35545844
    if not (raw32 or bc1 or bc3):
        raise ValueError("Local DDS is outside the native GPU intake contract")

    if raw32:
        red, blue = _u32(blob, 92), _u32(blob, 100)
        bgra = red == 0x00ff0000 and blue == 0x000000ff
        if (_u32(blob, 88) != 32 or
                (not bgra and (red != 0x000000ff or blue != 0x00ff0000)) or
                _u32(blob, 96) != 0x0000ff00 or
                _u32(blob, 104) != 0xff000000 or
                _u32(blob, 20) != width * 4):
            raise ValueError("Local DDS is outside the native GPU intake contract")
        name = "BGRA8" if bgra else "RGBA8"
    else:
        if (height % 4 or any(_u32(blob, p) for p in (88, 92, 96, 100, 104))):
            raise ValueError("Local DDS is outside the native GPU intake contract")
        name = "BC3/DXT5" if bc3 else "BC1/DXT1"

    required_flags = (0x100f if raw32 else 0x81007) | (0x20000 if mip_flag else 0)
    if _u32(blob, 8) != required_flags:
        raise ValueError("Local DDS is outside the native GPU intake contract")

    file_bytes = 0
    base_bytes = 0
    w, h = width, height
    for level in range(mip_count):
        if raw32:
            level_bytes = w * h * 4
        else:
            level_bytes = ((w + 3) // 4) * ((h + 3) // 4) * (16 if bc3 else 8)
        if level == 0:
            base_bytes = level_bytes
        if file_bytes > MAX_INPUT_BYTES - level_bytes:
            raise ValueError("Local DDS is outside the native GPU intake contract")
        file_bytes += level_bytes
        w, h = max(1, w // 2), max(1, h // 2)
    if ((not raw32 and _u32(blob, 20) != base_bytes) or
            len(blob) != DDS_HEADER_BYTES + file_bytes):
        raise ValueError("Local DDS is outside the native GPU intake contract")

    return {
        "format": name,
        "width": width,
        "height": height,
        "declared_mip_levels": mip_count,
        "dds_file_bytes": len(blob),
        "rgba8_level0_bytes": width * height * 4,
        "mip_upload": "base-level-only",
    }


def examine_local_slots(root: Path) -> dict[str, Any]:
    """Classify only hardcoded material0/1.dds, never enumerate private names.

    A missing slot explicitly means the native demo's synthetic fallback.
    Any present but rejected file aborts *all* preflight reporting. Both
    reads use the same no-follow descriptor, with metadata checks.
    """
    if not isinstance(root, Path) or not NOFOLLOW or not DIRECTORY:
        raise ValueError("Private GPU intake requires a local no-follow directory")
    try:
        root_fd = os.open(root, READ | NOFOLLOW | DIRECTORY)
    except OSError:
        raise ValueError("Unable to safely open private GPU texture directory") from None
    try:
        directory_start = os.fstat(root_fd)
        slots = []
        for slot, filename in enumerate(SLOTS):
            try:
                observed = os.stat(filename, dir_fd=root_fd, follow_symlinks=False)
            except FileNotFoundError:
                slots.append({"material_slot": slot, "status": "synthetic-fallback"})
                continue
            except OSError:
                raise ValueError("Private GPU texture entry changed") from None
            if not stat.S_ISREG(observed.st_mode):
                raise ValueError("Private GPU texture entry is not a regular file")
            if not DDS_HEADER_BYTES <= observed.st_size <= MAX_FILE_BYTES:
                raise ValueError("Local DDS is outside the native GPU intake contract")
            with open_regular_at(root_fd, filename) as (stream, opened):
                if _identity(observed) != _identity(opened):
                    raise ValueError("Private GPU texture entry changed")
                first = stream.read(opened.st_size + 1)
                stream.seek(0)
                second = stream.read(opened.st_size + 1)
                if (len(first) != opened.st_size or first != second or
                        len(second) != opened.st_size):
                    raise ValueError("Private GPU texture bytes changed during preflight")
                desc = classify_classic_dds(first)
                try:
                    final = os.stat(filename, dir_fd=root_fd,
                                    follow_symlinks=False)
                except OSError:
                    raise ValueError("Private GPU texture entry changed") from None
                if _identity(observed) != _identity(final):
                    raise ValueError("Private GPU texture entry changed")
                slots.append({"material_slot": slot, "status": "classic-dds-compatible",
                              **desc})
        if _identity(directory_start) != _identity(os.fstat(root_fd)):
            raise ValueError("Private GPU texture directory changed during preflight")
        return {
            "schema": "foj-gpu-local-dds-preflight-v1",
            "source": "private-fixed-slot-files-only",
            "purpose": "research-deko3d-two-material-dds-intake",
            "slots": slots,
            "native_loader_contract_checked": True,
            "ps3_resource_format_verified": False,
            "foj_material_mapping_verified": False,
            "nintendo_switch_execution_verified": False,
        }
    finally:
        os.close(root_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path,
                        help="Local private directory with material0.dds/material1.dds")
    parser.add_argument("--output", type=Path,
                        help="Optional NEW metadata-only report; no source names or bytes")
    args = parser.parse_args()
    try:
        report = examine_local_slots(args.directory)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    # This output never includes original paths, raw bytes, or fingerprints.
    body = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        try:
            with args.output.open("x", encoding="utf-8") as output:
                output.write(body)
        except FileExistsError:
            parser.error("Preflight report output must be a new file")
        except OSError:
            parser.error("Unable to publish private preflight report")
    print(body, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
