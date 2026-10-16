#!/usr/bin/env python3
"""Validate NRO0 layout/segment extents; does not prove runtime compatibility."""
import argparse
import struct
import sys
from pathlib import Path


def validate_nro(data: bytes) -> dict:
    if len(data) < 0x80:
        raise ValueError("Truncated NRO header")
    if data[0x10:0x14] != b"NRO0":
        raise ValueError("Missing NRO0 magic at 0x10")
    declared = struct.unpack_from("<I", data, 0x18)[0]
    if declared > len(data) or declared < 0x80:
        raise ValueError("NRO declared size is outside physical file")
    segments = {}
    for label, offset in (("text", 0x20), ("rodata", 0x28), ("data", 0x30)):
        start, size = struct.unpack_from("<II", data, offset)
        if start > declared or size > declared - start:
            raise ValueError(f"{label} segment outside declared NRO size")
        segments[label] = {"offset": start, "size": size}
    return {"file_size": len(data), "declared_size": declared, "segments": segments}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("nro", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate_nro(args.nro.read_bytes())
    except (OSError, ValueError) as exc:
        print(f"Invalid NRO: {exc}", file=sys.stderr)
        return 2
    print(f"Validated NRO0 header: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
