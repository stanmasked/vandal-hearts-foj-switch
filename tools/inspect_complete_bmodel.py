#!/usr/bin/env python3
"""Read-only decoder of every *mesh section* in FoJ's original .bmodel files.

Based on structural validation across all 583 resources in the user's FoJ
PS3 NPEB00148 PSARC: 1380 mesh sections, 583431 triangles. Uses no game
bytes in source. Materials and their texture basenames are read as links,
not written/extracted. A trailing 0x0A/0x0C block remains unparsed.
All geometry is triangle soup with BE float32 and BE uint16 indices.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
import sys

MAX_MODEL_BYTES = 4_000_000
MAX_SHAPES = 64
MAX_VERTICES = 65535
MAX_MATERIALS = 128


class ModelFormatError(ValueError):
    pass


@dataclass(frozen=True)
class MeshSection:
    name: str
    material: str
    vertex_count: int
    triangle_count: int
    xyz_offset: int
    uv_offset: int
    normal_offset: int
    triangle_normal_offset: int
    index_offset: int
    influences_per_vertex: int
    bone_index_max: int | None
    bounds_six: tuple[float, ...]


@dataclass(frozen=True)
class MaterialLink:
    name: str
    texture_names: tuple[str, ...]


@dataclass(frozen=True)
class CompleteModel:
    shapes: tuple[MeshSection, ...]
    materials: tuple[MaterialLink, ...]
    footer_tag: int
    footer_bytes: int

    def report(self) -> dict:
        return {
            "shape_count": len(self.shapes),
            "vertex_count": sum(s.vertex_count for s in self.shapes),
            "triangle_count": sum(s.triangle_count for s in self.shapes),
            "skinned_shape_count": sum(s.influences_per_vertex > 0 for s in self.shapes),
            "shape_summaries": [{
                "name": s.name, "material": s.material,
                "vertices": s.vertex_count, "triangles": s.triangle_count,
                "influences_per_vertex": s.influences_per_vertex,
                "maximum_bone_index": s.bone_index_max,
                "bounding_fields": list(s.bounds_six),
            } for s in self.shapes],
            "material_links": [{
                "name": m.name, "texture_basenames": list(m.texture_names)
            } for m in self.materials],
            "footer_tag": f"0x{self.footer_tag:02x}",
            "unparsed_footer_bytes": self.footer_bytes,
            "note": "Mesh/material tables decoded; transforms, skeleton and footer semantics unverified.",
        }


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.p = 0

    def take(self, length: int) -> bytes:
        if length < 0 or length > len(self.data) - self.p:
            raise ModelFormatError("Truncated BMODEL")
        payload = self.data[self.p:self.p + length]
        self.p += length
        return payload

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return int.from_bytes(self.take(2), "big")

    def expect(self, data: bytes):
        if self.take(len(data)) != data:
            raise ModelFormatError("Unexpected BMODEL structure tag")

    def text(self) -> str:
        n = self.u16()
        if not 1 <= n <= 255:
            raise ModelFormatError("Invalid model string length")
        try:
            value = self.take(n).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ModelFormatError("BMODEL text is not UTF-8") from exc
        if any(ord(ch) < 32 or ord(ch) > 126 for ch in value):
            raise ModelFormatError("Non-printable BMODEL identifier")
        return value

    def array(self, tag: int, elements: int, stride: int,
              expected: int | None = None) -> tuple[int, int]:
        if self.u8() != tag:
            raise ModelFormatError(f"Unexpected geometry tag (expected 0x{tag:02x})")
        n = self.u16()
        if not (1 <= n <= MAX_VERTICES) or (expected is not None and n != expected):
            raise ModelFormatError("Geometry attribute count mismatch")
        if tag == 0x05:
            self.expect(b"\x00\x03")
        offset = self.p
        self.take(n * stride)
        return n, offset


def decode_model(data: bytes) -> CompleteModel:
    if not isinstance(data, bytes) or len(data) < 50 or len(data) > MAX_MODEL_BYTES:
        raise ModelFormatError("Missing or oversized BMODEL")
    r = Reader(data)
    r.expect(b"\x0b\x09\x00")
    shape_count = r.u8()
    if not 1 <= shape_count <= MAX_SHAPES:
        raise ModelFormatError("Unexpected BMODEL shape count")
    shapes: list[MeshSection] = []
    for i in range(shape_count):
        if i:
            r.expect(b"\x07")  # next shape in sequence
        r.expect(b"\x01\x20\x00")
        name = r.text()
        n, xyz = r.array(0x02, 3, 12)
        if n % 3:
            raise ModelFormatError("Triangle-soup vertex count must be divisible by 3")
        _, uv = r.array(0x05, 2, 8, n)
        _, normal = r.array(0x10, 3, 12, n)
        _, tri_normal = r.array(0x15, 3, 12, n // 3)
        _, index = r.array(0x04, 1, 2, n)

        # All tested shape index buffers are sequential 0..N-1. Reject
        # unverified variants instead of silently rendering wrong geometry.
        for j, (value,) in enumerate(struct.iter_unpack(
            ">H", memoryview(data)[index:index + n * 2]
        )):
            if value != j:
                raise ModelFormatError("Unsupported nonsequential triangle indices")

        influence_count = 0
        bone_index_max = None
        if r.p < len(data) and data[r.p] == 0x0f:
            r.u8()
            total = r.u16()
            influence_count = r.u16()
            if not 1 <= influence_count <= 16 or total != n * influence_count:
                raise ModelFormatError("Invalid vertex bone influence table length")
            bone_index_max = 0
            for vertex in range(n):
                total_weight = 0.0
                for _ in range(influence_count):
                    bone = r.u16()
                    weight, = struct.unpack(">f", r.take(4))
                    if bone > bone_index_max:
                        bone_index_max = bone
                    if not math.isfinite(weight) or weight < -0.001 or weight > 1.001:
                        raise ModelFormatError("Invalid skinning weight")
                    total_weight += weight
                if abs(total_weight - 1.0) > 0.001:
                    raise ModelFormatError("Vertex skinning weights do not sum to 1")

        r.expect(b"\x14")
        material = r.text()
        r.expect(b"\x21")
        bounds = struct.unpack(">6f", r.take(24))
        if not all(math.isfinite(x) and abs(x) < 1e7 for x in bounds):
            raise ModelFormatError("Invalid geometry bounding float")
        shapes.append(MeshSection(name, material, n, n // 3,
                                  xyz, uv, normal, tri_normal, index,
                                  influence_count, bone_index_max, bounds))

    r.expect(b"\x07")  # material bundle
    materials: list[MaterialLink] = []
    while r.p < len(data) and data[r.p] == 0x06:
        if len(materials) >= MAX_MATERIALS:
            raise ModelFormatError("Too many materials")
        r.u8()
        material = r.text()
        count = r.u16()
        if count > 32:
            raise ModelFormatError("Too many texture references in one material")
        textures = tuple(r.text() for _ in range(count))
        materials.append(MaterialLink(material, textures))
    if not materials or r.p >= len(data) or data[r.p] not in (0x0a, 0x0c):
        raise ModelFormatError("Unsupported material bundle/footer")
    footer_tag = data[r.p]
    footer_size = len(data) - r.p
    return CompleteModel(tuple(shapes), tuple(materials),
                         footer_tag, footer_size)


def resolve_textures(model_path: str, materials: tuple[MaterialLink, ...],
                     manifest: list[str]) -> dict[str, list[dict]]:
    """Prefer identical resource directory; never choose arbitrary duplicates."""
    directory = model_path.rsplit("/", 1)[0] + "/"
    indexed: dict[str, list[str]] = {}
    for path in manifest:
        if path.lower().endswith(".tga"):
            indexed.setdefault(path.rsplit("/", 1)[-1].lower(), []).append(path)
    result: dict[str, list[dict]] = {}
    for material in materials:
        choices = []
        for base in material.texture_names:
            matches = indexed.get(base.lower(), [])
            local = [path for path in matches if path.rsplit("/", 1)[0] + "/" == directory]
            if len(local) == 1:
                selected, reason = local[0], "same_directory"
            elif len(matches) == 1:
                selected, reason = matches[0], "unique_basename"
            else:
                selected, reason = None, "ambiguous" if matches else "not_found"
            choices.append({
                "basename": base,
                "path": selected,
                "resolution": reason,
                "candidate_count": len(matches),
            })
        result[material.name] = choices
    return result


def inspect_local_pkg(parts: list[Path], asset: str) -> dict:
    if (not asset.startswith("data/") or
        not asset.lower().endswith(".bmodel") or
        "\\" in asset or ".." in asset.split("/")):
        raise ValueError("Invalid .bmodel path")
    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip,
    )
    from tools.inspect_split_pkg import JoinedParts
    with JoinedParts(parts) as joined:
        pos, size = unpack_stored_zip(joined)
        pkg = DebugPKG(joined, pos, size)
        items = [item for item in pkg.items()
                 if item["path"].lower() == "usrdir/cdata.psarc"]
        if len(items) != 1:
            raise FormatError("Missing unique cdata.psarc")
        archive = PSARC(pkg, items[0]["offset"], items[0]["size"])
        names = archive.manifest()
        if names.count(asset) != 1:
            raise FormatError("Missing/duplicate model path")
        payload = archive.entry_data(names.index(asset) + 1, limit=MAX_MODEL_BYTES)
        model = decode_model(payload)
        report = model.report()
        report["asset"] = asset
        report["texture_bindings"] = resolve_textures(asset, model.materials, names)
        return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("parts", nargs="+", type=Path)
    ap.add_argument("--asset", required=True, help="data/.../example.bmodel")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        report = inspect_local_pkg(args.parts, args.asset)
    except (OSError, ValueError) as exc:
        print(f"Model inspection error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{report['asset']}: {report['shape_count']} shapes, "
              f"{report['triangle_count']} triangles")
        print("Materials:", report["texture_bindings"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
