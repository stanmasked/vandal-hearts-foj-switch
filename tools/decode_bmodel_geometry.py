#!/usr/bin/env python3
"""Inspect/export the *first* verified triangle section in FoJ .bmodel files.

Discovered from the user's original PS3 NPEB00148 archive. This parser supports
the first shape only and deliberately does NOT claim to decode later sections,
materials, transforms, skeletons, or animations.

No game data is embedded. --output is optional, explicit, local-only, refuses
overwrites, and is NEVER invoked by CI with real commercial files.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
import sys

MAX_BMODEL_BYTES = 2_000_000
MAX_VERTICES = 65535


class BModelError(ValueError):
    """Model format is truncated or does not match the verified subset."""


@dataclass(frozen=True)
class FirstShape:
    name: str
    vertices: tuple[tuple[float, float, float], ...]
    uvs: tuple[tuple[float, float], ...]
    normals: tuple[tuple[float, float, float], ...]
    face_normals: tuple[tuple[float, float, float], ...]
    indices: tuple[int, ...]
    section_end: int

    def summary(self) -> dict:
        low = [min(v[d] for v in self.vertices) for d in range(3)]
        high = [max(v[d] for v in self.vertices) for d in range(3)]
        uv_low = [min(v[d] for v in self.uvs) for d in range(2)]
        uv_high = [max(v[d] for v in self.uvs) for d in range(2)]
        worst_normal_delta = max(
            abs(math.sqrt(sum(v*v for v in normal)) - 1)
            for normal in self.normals
        )
        return {
            "first_shape_name": self.name,
            "vertex_count": len(self.vertices),
            "triangle_count": len(self.indices) // 3,
            "indexed_vertex_count": len(self.indices),
            "bounds_xyz": {"minimum": low, "maximum": high},
            "uv_bounds": {"minimum": uv_low, "maximum": uv_high},
            "maximum_normal_length_error": worst_normal_delta,
            "first_shape_end_offset": self.section_end,
            "note": "First shape only. Remaining .bmodel sections unparsed.",
        }


def decode_first_shape(data: bytes) -> FirstShape:
    if not isinstance(data, bytes) or len(data) < 32:
        raise BModelError("Missing/short model data")
    if len(data) > MAX_BMODEL_BYTES:
        raise BModelError("Model file exceeds research limit")
    if data[:3] != b"\x0b\x09\x00" or data[4:7] != b"\x01\x20\x00":
        raise BModelError("Unrecognized .bmodel file preamble")
    if not (1 <= data[3] <= 64 and 1 <= data[7] <= 127):
        raise BModelError("Invalid part count or name length")
    if 8 + data[7] >= len(data):
        raise BModelError("First shape name extends beyond file")
    name_raw = data[8:8 + data[7]]
    try:
        name = name_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BModelError("First shape name is not UTF-8") from exc
    if not name or any(ord(c) < 32 or ord(c) > 126 for c in name):
        raise BModelError("First shape name is not printable")
    p = 8 + data[7]

    def require(n: int):
        if n < 0 or p + n > len(data):
            raise BModelError("Truncated first shape attribute section")

    def array_tag(expected: int, expected_count: int | None = None) -> int:
        nonlocal p
        require(3)
        tag, count = struct.unpack_from(">BH", data, p)
        if tag != expected or count < 1 or count > MAX_VERTICES:
            raise BModelError(f"Expected geometry tag 0x{expected:02x}")
        if expected_count is not None and count != expected_count:
            raise BModelError("Attribute/vertex count mismatch")
        p += 3
        return count

    def floats(count: int, dims: int) -> tuple[tuple[float, ...], ...]:
        nonlocal p
        require(count * dims * 4)
        values = struct.iter_unpack(">" + "f"*dims,
                                    memoryview(data)[p:p + count*dims*4])
        result = tuple(values)
        if len(result) != count or not all(
            math.isfinite(x) and abs(x) <= 1_000_000
            for row in result for x in row
        ):
            raise BModelError("Non-finite/unreasonable geometry attribute")
        p += count*dims*4
        return result

    count = array_tag(0x02)
    if count % 3:
        raise BModelError("First shape vertex count not divisible by three")
    vertices = floats(count, 3)

    array_tag(0x05, count)
    require(2)
    if data[p:p + 2] != b"\x00\x03":
        raise BModelError("Unexpected UV array prefix")
    p += 2
    uvs = floats(count, 2)

    array_tag(0x10, count)
    normals = floats(count, 3)
    if not all(
        abs(sum(c*c for c in vector) - 1) <= 0.02 for vector in normals
    ):
        raise BModelError("Normal vectors are not near unit length")

    face_count = array_tag(0x15, count//3)
    face_normals = floats(face_count, 3)

    array_tag(0x04, count)
    require(count * 2)
    indices = struct.unpack_from(">" + "H"*count, data, p)
    if any(idx != position for position, idx in enumerate(indices)):
        raise BModelError("Unrecognized first-shape index organization")
    p += count * 2
    return FirstShape(name, vertices, uvs, normals, face_normals, indices, p)


def write_local_obj(shape: FirstShape, destination: Path,
                    *, flip_v: bool = False) -> None:
    """Export only user-selected first geometry section, never overwrite."""
    if destination.suffix.lower() != ".obj":
        raise ValueError("Only .obj output supported")
    if not destination.parent.is_dir() or destination.is_symlink():
        raise ValueError("Output parent unavailable or path is symlink")
    # Exclusive creation prevents overwriting existing local assets.
    with destination.open("x", encoding="utf-8", newline="\n") as out:
        out.write("# Original FoJ first-shape geometry, user-local research only.\n")
        out.write("# No verified material binding, skeleton or transforms.\n")
        safe_name = shape.name.replace(" ", "_").replace("#", "_")
        out.write("o " + safe_name + "\n")
        for x, y, z in shape.vertices:
            out.write(f"v {x:.9g} {y:.9g} {z:.9g}\n")
        for u, v in shape.uvs:
            out.write(f"vt {u:.9g} {1-v if flip_v else v:.9g}\n")
        for x, y, z in shape.normals:
            out.write(f"vn {x:.9g} {y:.9g} {z:.9g}\n")
        for i in range(0, len(shape.indices), 3):
            ids = [shape.indices[i+j] + 1 for j in range(3)]
            out.write("f " + " ".join(f"{n}/{n}/{n}" for n in ids) + "\n")


def inspect_split_archive_asset(
    parts: list[Path], asset: str, destination: Path | None = None,
    *, flip_v: bool = False,
) -> dict:
    """Read a particular .bmodel in memory from user's local split PKG ZIP."""
    if (not asset.startswith("data/") or
        not asset.lower().endswith(".bmodel") or
        "\\" in asset or ".." in asset.split("/")):
        raise ValueError("Unsafe/unsupported in-archive .bmodel path")
    if destination is not None and (
        destination.exists() or destination.is_symlink()
        or destination.suffix.lower() != ".obj"
        or not destination.parent.is_dir()
    ):
        raise ValueError("Destination must be a new local .obj file")
    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip
    )
    from tools.inspect_split_pkg import JoinedParts
    with JoinedParts(parts) as stream:
        offset, length = unpack_stored_zip(stream)
        pkg = DebugPKG(stream, offset, length)
        matches = [entry for entry in pkg.items()
                   if entry["path"].lower() == "usrdir/cdata.psarc"]
        if len(matches) != 1:
            raise FormatError("No unique game cdata.psarc")
        archive = PSARC(pkg, matches[0]["offset"], matches[0]["size"])
        manifest = archive.manifest()
        if manifest.count(asset) != 1:
            raise FormatError("Model not found or duplicated")
        index = manifest.index(asset) + 1
        data = archive.entry_data(index, limit=MAX_BMODEL_BYTES)
        shape = decode_first_shape(data)
    if destination is not None:
        write_local_obj(shape, destination, flip_v=flip_v)
    return {
        "asset": asset,
        "source_bytes": len(data),
        "shape": shape.summary(),
        "exported_local_obj": destination.name if destination else None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path,
                        help="Ordered user-local .pkg.zip.001/.002 chunks")
    parser.add_argument("--asset", required=True,
                        help="Exact data/.../name.bmodel resource path")
    parser.add_argument("--output", type=Path,
                        help="Optional explicit, NEW local .obj filename")
    parser.add_argument("--flip-v", action="store_true",
                        help="Flip texture V coordinate only in optional OBJ")
    args = parser.parse_args(argv)
    try:
        report = inspect_split_archive_asset(
            args.parts, args.asset, args.output, flip_v=args.flip_v
        )
    except (BModelError, OSError, ValueError) as exc:
        print(f"BMODEL decode error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
