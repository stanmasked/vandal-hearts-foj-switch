#!/usr/bin/env python3
"""Convert *our synthetic* binary P6 PPM test image to an RGBA PNG.

Small, dependency-free helper for CI evidence. Supports no other PPM variants.
"""
from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    )


def ppm_to_png(ppm: bytes) -> bytes:
    parts = ppm.split(b"\n", 3)
    if len(parts) != 4 or parts[0] != b"P6" or parts[2] != b"255":
        raise ValueError("Only P6 PPM with max-value 255 is supported")
    try:
        width, height = (int(part) for part in parts[1].split())
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid PPM dimensions") from exc
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise ValueError("PPM dimensions are outside the safety bounds")
    pixels = parts[3]
    if len(pixels) != width * height * 3:
        raise ValueError("Unexpected number of PPM pixel bytes")

    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)  # PNG filter: none
        row = pixels[y * width * 3:(y + 1) * width * 3]
        for offset in range(0, len(row), 3):
            scanlines.extend(row[offset:offset + 3])
            scanlines.append(255)
    return (
        PNG_MAGIC
        + _chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(scanlines, 9))
        + _chunk(b"IEND", b"")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_ppm", type=Path)
    parser.add_argument("output_png", type=Path)
    args = parser.parse_args()
    args.output_png.write_bytes(ppm_to_png(args.input_ppm.read_bytes()))
    print(f"Created preview: {args.output_png}")


if __name__ == "__main__":
    main()
