#!/usr/bin/env python3
"""Private, opt-in conversion of original BMODEL into portable FOJRM001.

Only the user's own local PS3 asset is read. The output preserves real
geometry, UVs, normals, optional indexed skin weights and bind-pose hierarchy.
Unskinned static meshes use zero bones and zero influences per vertex. This
DOES NOT recover original engine space, shader, material, joint retargeting,
nor rig/animation pairing. Binary data is proprietary: never commit it.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys

from tools.decode_rig_banim import parse_bmodel_rig
from tools.inspect_complete_bmodel import (
    MAX_MODEL_BYTES, ModelFormatError, decode_model,
)

MAGIC = b"FOJRM001"
VERSION = 1
MAX_BONES = 256
MAX_VERTICES = 20000
MAX_SECTIONS = 64
MAX_INFLUENCES = 5
HEADER = struct.Struct("<8s5I")
BONE = struct.Struct("<i4f3f")
SECTION = struct.Struct("<II")
VERTEX = struct.Struct("<3f2f3fI")
INFLUENCE = struct.Struct("<If")


def pack_rig_mesh(data: bytes) -> tuple[bytes, dict]:
    """Build a bounded, little-endian format with explicit fixed-size records.

    No game assets are present in code. The returned bytes are protected
    original content and must be kept on user-controlled local storage.
    """
    model = decode_model(data)
    rig = parse_bmodel_rig(data[-model.footer_bytes:])
    bones = rig.bones
    vertex_count = sum(s.vertex_count for s in model.shapes)
    if (len(bones) > MAX_BONES or
        not 1 <= len(model.shapes) <= MAX_SECTIONS or
        not 3 <= vertex_count <= MAX_VERTICES):
        raise ValueError("Model rig/vertex/section counts outside research limits")
    if not bones and any(s.influences_per_vertex for s in model.shapes):
        raise ValueError("Skinned vertices require an embedded rig")
    output = bytearray(HEADER.pack(MAGIC, VERSION, len(bones),
                                   vertex_count, len(model.shapes), 0))
    for b in bones:
        parent = -1 if b.parent is None else b.parent
        output.extend(BONE.pack(parent, *b.rotation_xyzw, *b.translation_xyz))
    offset = 0
    for section in model.shapes:
        if section.vertex_count % 3:
            raise ModelFormatError("Non-triangulated shape")
        output.extend(SECTION.pack(offset, section.vertex_count))
        offset += section.vertex_count
    weighted_vertices = 0
    for section in model.shapes:
        n = section.vertex_count
        count = section.influences_per_vertex
        if not 0 <= count <= MAX_INFLUENCES:
            raise ValueError("Skin influences per vertex exceed native limit")
        influence_offset = section.index_offset + 2*n
        if count:
            if data[influence_offset] != 0x0f:
                raise ModelFormatError("Skinning header missing")
            expected, actual = struct.unpack_from(">HH", data, influence_offset + 1)
            if actual != count or expected != n*count:
                raise ModelFormatError("Unexpected skinning count")
            influence_offset += 5
        for i in range(n):
            xyz = struct.unpack_from(">3f", data, section.xyz_offset + i*12)
            uv = struct.unpack_from(">2f", data, section.uv_offset + i*8)
            normal = struct.unpack_from(">3f", data, section.normal_offset + i*12)
            if not all(math.isfinite(v) and abs(v) < 1_000_000
                       for v in (*xyz, *uv, *normal)):
                raise ModelFormatError("Non-finite/out-of-range vertex attribute")
            output.extend(VERTEX.pack(*xyz, *uv, *normal, count))
            total = 0.
            for j in range(MAX_INFLUENCES):
                if j < count:
                    bone, weight = struct.unpack_from(
                        ">Hf", data, influence_offset + (i*count + j)*6
                    )
                    if bone >= len(bones) or not math.isfinite(weight) or weight < 0:
                        raise ModelFormatError("Bone index / weight invalid")
                    total += weight
                    output.extend(INFLUENCE.pack(bone, weight))
                else:
                    output.extend(INFLUENCE.pack(0, 0.))
            if count:
                weighted_vertices += 1
                if abs(total - 1) > 0.002:
                    raise ModelFormatError("Vertex skin weights do not sum to one")
    expected_size = (HEADER.size + len(bones)*BONE.size +
                     len(model.shapes)*SECTION.size +
                     vertex_count*(VERTEX.size + 5*INFLUENCE.size))
    if len(output) != expected_size:
        raise AssertionError("FOJRM001 byte layout mismatch")
    return bytes(output), {
        "bones": len(bones), "mesh_kind": "static" if not bones else "rigged",
        "sections": len(model.shapes),
        "vertices": vertex_count, "triangles": vertex_count//3,
        "weighted_vertices": weighted_vertices,
        "bytes": len(output),
        "format": "FOJRM001",
        "warning": "Private original game geometry; do NOT share or upload.",
    }


def export_local_rigmesh(parts: list[Path], asset: str, destination: Path) -> dict:
    if (not asset.startswith("data/") or
        not asset.lower().endswith(".bmodel") or
        "\\" in asset or ".." in asset.split("/")):
        raise ValueError("Unsafe BMODEL asset path")
    if destination.suffix.lower() != ".fojrm" or not destination.parent.is_dir():
        raise ValueError("Output must be a new .fojrm in an existing directory")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Refusing to overwrite existing local rig mesh")

    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip,
    )
    from tools.inspect_split_pkg import JoinedParts
    with JoinedParts(parts) as stream:
        beginning, size = unpack_stored_zip(stream)
        pkg = DebugPKG(stream, beginning, size)
        matches = [item for item in pkg.items()
                   if item["path"].lower() == "usrdir/cdata.psarc"]
        if len(matches) != 1:
            raise FormatError("Missing unique PSARC archive")
        arc = PSARC(pkg, matches[0]["offset"], matches[0]["size"])
        names = arc.manifest()
        if names.count(asset) != 1:
            raise FormatError("Model path missing or ambiguous")
        resource = arc.entry_data(names.index(asset)+1, limit=MAX_MODEL_BYTES)
        packed, stats = pack_rig_mesh(resource)
    with destination.open("xb") as handle:
        handle.write(packed)
    return {"source_asset": asset, "local_file": destination.name, **stats}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="+", type=Path,
                        help="Ordered user-local .pkg.zip.001/.002 fragments")
    parser.add_argument("--asset", required=True, help="Exact original .bmodel path")
    parser.add_argument("--output", required=True, type=Path,
                        help="New private .fojrm filename, never overwritten")
    args = parser.parse_args(argv)
    try:
        report = export_local_rigmesh(args.parts, args.asset, args.output)
    except (OSError, ValueError) as exc:
        print(f"Rig mesh export error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
