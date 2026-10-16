#!/usr/bin/env python3
"""Validate FoJ BMODEL full mesh/material tables across local PSARC resources.

This reports *aggregate statistics only*. It never exports original geometry,
skeletons or textures. Game package remains in user-controlled local files.
The model's trailing 0x0a/0x0c records are intentionally not interpreted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Callable

from tools.inspect_complete_bmodel import (
    ModelFormatError, decode_model, resolve_textures,
)

MAX_AUDIT_FILES = 2000


def audit_model_records(
    manifest: list[str],
    fetch: Callable[[str], bytes],
    *,
    max_models: int = 1000,
) -> dict:
    if max_models < 1 or max_models > MAX_AUDIT_FILES:
        raise ValueError("Invalid BMODEL audit limit")
    names = [name for name in manifest if name.lower().endswith(".bmodel")]
    if len(names) > MAX_AUDIT_FILES:
        raise ValueError("BMODEL manifest count exceeds audit safety limit")

    figures: Counter[str] = Counter()
    contributions: Counter[str] = Counter()
    suffixes: Counter[str] = Counter()
    errors = 0
    all_textures: set[str] = set()
    for filename in names[:max_models]:
        try:
            model = decode_model(fetch(filename))
        except (OSError, ValueError, TypeError):
            errors += 1
            continue
        figures["models"] += 1
        figures["shapes"] += len(model.shapes)
        figures["triangles"] += sum(s.triangle_count for s in model.shapes)
        figures["vertices"] += sum(s.vertex_count for s in model.shapes)
        figures["skinned_shapes"] += sum(
            s.influences_per_vertex > 0 for s in model.shapes
        )
        figures["skinned_models"] += int(any(
            s.influences_per_vertex > 0 for s in model.shapes
        ))
        figures["bone_influence_records"] += sum(
            s.vertex_count * s.influences_per_vertex for s in model.shapes
        )
        figures["material_entries"] += len(model.materials)
        suffixes[f"0x{model.footer_tag:02x}"] += 1
        resolved = resolve_textures(filename, model.materials, manifest)
        for links in resolved.values():
            for link in links:
                contributions[link["resolution"]] += 1
                all_textures.add(link["basename"].lower())

    return {
        "manifest_bmodel_count": len(names),
        "inspected_count": min(len(names), max_models),
        "success_count": figures["models"],
        "error_count": errors,
        "total_shapes": figures["shapes"],
        "total_triangles": figures["triangles"],
        "total_vertices": figures["vertices"],
        "models_with_skinning": figures["skinned_models"],
        "shapes_with_skinning": figures["skinned_shapes"],
        "total_bone_influences": figures["bone_influence_records"],
        "material_entries": figures["material_entries"],
        "texture_references": sum(contributions.values()),
        "unique_texture_basenames": len(all_textures),
        "texture_path_resolution": dict(sorted(contributions.items())),
        "footer_tags_uninterpreted": dict(sorted(suffixes.items())),
        "warning": "No geometry, skeleton, original textures or protected assets in report.",
    }


def audit_split_package(parts: list[Path], *, max_models: int = 1000) -> dict:
    from tools.inspect_debug_pkg_assets import (
        DebugPKG, FormatError, PSARC, unpack_stored_zip,
    )
    from tools.inspect_split_pkg import JoinedParts
    with JoinedParts(parts) as stream:
        begin, length = unpack_stored_zip(stream)
        pkg = DebugPKG(stream, begin, length)
        archive_items = [
            item for item in pkg.items()
            if item["path"].lower() == "usrdir/cdata.psarc"
        ]
        if len(archive_items) != 1:
            raise FormatError("Missing unique cdata.psarc")
        resource = archive_items[0]
        archive = PSARC(pkg, resource["offset"], resource["size"])
        manifest = archive.manifest()
        path_to_index = {name: i + 1 for i, name in enumerate(manifest)}

        def read_resource(name: str) -> bytes:
            return archive.entry_data(path_to_index[name], limit=4_000_000)

        return audit_model_records(manifest, read_resource, max_models=max_models)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", type=Path, nargs="+", help="Ordered ZIP fragments")
    parser.add_argument("--max-models", type=int, default=1000)
    args = parser.parse_args(argv)
    try:
        report = audit_split_package(args.parts, max_models=args.max_models)
    except (OSError, ValueError) as exc:
        print(f"Full BMODEL audit error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
