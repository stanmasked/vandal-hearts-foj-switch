#!/usr/bin/env python3
"""Offline, metadata-only DDS container-range and pointer-reference hints.

Input comes from tools.foj_texture_probe. This script never decodes textures,
extracts payloads, alters game files, or asserts proprietary container formats.
32-bit LE/BE matches in a short file prefix are only possible pointers.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path, PurePosixPath
import stat
from typing import Any

HEADER_BYTES = 128
DEFAULT_PREFIX_BYTES = 65536
MAX_PREFIX_BYTES = 1048576
DEFAULT_MAX_POINTERS_PER_CANDIDATE = 16


def _safe_relative_path(raw: str) -> PurePosixPath:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ValueError("Invalid relative path in candidate report")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in ("..", ".") for part in raw.split("/")):
        raise ValueError("Candidate path is not a safe relative filename")
    if not path.parts or any(part in ("", ".") for part in path.parts):
        raise ValueError("Invalid candidate relative path")
    return path


def _read_prefix(root: Path, relative: PurePosixPath, limit: int) -> bytes:
    """Reject symlinks in any path component and non-regular files."""
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Candidate path traverses a symlink")
    try:
        st = cursor.lstat()
    except OSError as exc:
        raise ValueError("Candidate file is unavailable") from exc
    if not stat.S_ISREG(st.st_mode):
        raise ValueError("Candidate path is not a regular file")
    with cursor.open("rb") as fp:
        return fp.read(limit)


def build_relations(manifest: dict[str, Any], *, root: Path | None = None,
                    prefix_bytes: int = DEFAULT_PREFIX_BYTES,
                    max_pointers_per_candidate: int =
                    DEFAULT_MAX_POINTERS_PER_CANDIDATE) -> dict[str, Any]:
    """Build layout hypotheses, optionally probing prefix-aligned pointers.

    No offsets/lengths in an untrusted report are treated as proven locations.
    """
    if manifest.get("schema") != "foj-texture-candidates-v1":
        raise ValueError("Expected a stage-141 DDS candidate manifest")
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("Manifest candidates must be a list")
    if not 4 <= prefix_bytes <= MAX_PREFIX_BYTES:
        raise ValueError("Pointer prefix size must be from 4 B to 1 MiB")
    if not 1 <= max_pointers_per_candidate <= 128:
        raise ValueError("Pointer matches per candidate must be 1..128")
    if root is not None:
        if root.is_symlink() or not root.is_dir():
            raise ValueError("Pointer scan root must be a non-symlink directory")
        root = root.resolve()

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    formats = Counter()
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("Invalid DDS candidate record")
        relative = str(_safe_relative_path(item.get("relative_path")))
        offset = item.get("offset")
        size = item.get("expected_payload_bytes")
        fmt = item.get("format_candidate")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("Invalid DDS candidate offset")
        if size is not None and (isinstance(size, bool) or not
                                 isinstance(size, int) or size < 0):
            raise ValueError("Invalid DDS candidate payload length")
        if not isinstance(fmt, str) or not fmt:
            raise ValueError("Invalid DDS format label")
        entry: dict[str, Any] = {
            "offset": offset,
            "format_candidate": fmt,
            "expected_payload_bytes": size,
            "candidate_span_end": offset + HEADER_BYTES + size
                if size is not None else None,
            "next_candidate_offset": None,
            "gap_to_next_candidate_bytes": None,
            "layout_hint": "last-candidate",
            "possible_32bit_offset_references": [],
        }
        grouped[relative].append(entry)
        formats[fmt] += 1

    containers = []
    total_candidates = 0
    total_refs = 0
    for relative in sorted(grouped):
        entries = sorted(grouped[relative], key=lambda c: c["offset"])
        total_candidates += len(entries)
        spans = [
            (e["offset"], e["candidate_span_end"] or (e["offset"] + HEADER_BYTES))
            for e in entries
        ]
        for i, entry in enumerate(entries[:-1]):
            following = entries[i + 1]["offset"]
            entry["next_candidate_offset"] = following
            if entry["candidate_span_end"] is None:
                entry["layout_hint"] = "size-unclassified"
                continue
            gap = following - entry["candidate_span_end"]
            entry["gap_to_next_candidate_bytes"] = gap
            entry["layout_hint"] = (
                "overlap" if gap < 0 else
                "adjacent" if gap == 0 else "separated")
        if root is not None:
            prefix = _read_prefix(root, _safe_relative_path(relative),
                                  prefix_bytes)
            # Only *4-byte aligned positions in the file prefix* count as
            # references. Skip words contained within candidate payloads.
            targets: dict[int, list[dict[str, Any]]] = defaultdict(list)
            for entry in entries:
                if HEADER_BYTES <= entry["offset"] <= 0xffffffff:
                    targets[entry["offset"]].append(entry)
            if targets:
                for word_pos in range(0, len(prefix) - 3, 4):
                    if any(a <= word_pos < b for a, b in spans):
                        continue
                    raw = prefix[word_pos:word_pos + 4]
                    for order in ("little", "big"):
                        value = int.from_bytes(raw, order)
                        for entry in targets.get(value, ()):
                            refs = entry["possible_32bit_offset_references"]
                            if len(refs) < max_pointers_per_candidate:
                                refs.append({
                                    "word_offset": word_pos,
                                    "byte_order": order,
                                    "interpretation": "possible-file-relative-offset",
                                })
                                total_refs += 1

        containers.append({
            "relative_path": relative,
            "candidate_count": len(entries),
            "candidates": entries,
        })
    return {
        "schema": "foj-texture-layout-hypotheses-v1",
        "source_schema": "foj-texture-candidates-v1",
        "status": "heuristic-only; not verified FoJ format or material mapping",
        "pointer_scan": "first-file-prefix-aligned-uint32-le-be" if root
                        else "disabled",
        "pointer_prefix_bytes": prefix_bytes if root else 0,
        "containers": containers,
        "summary": {
            "containers_with_dds_candidates": len(containers),
            "dds_candidates": total_candidates,
            "possible_pointer_matches": total_refs,
            "format_candidates": dict(sorted(formats.items())),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path,
                        help="Private stage-141 DDS candidate JSON")
    parser.add_argument("--output", type=Path, required=True,
                        help="Private local JSON layout report")
    parser.add_argument("--root", type=Path,
                        help="Optional same extracted root, for pointer hints")
    parser.add_argument("--pointer-prefix-bytes", type=int,
                        default=DEFAULT_PREFIX_BYTES)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.inventory.read_text(encoding="utf-8"))
        report = build_relations(
            manifest, root=args.root, prefix_bytes=args.pointer_prefix_bytes)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"Layout candidates: {report['summary']['dds_candidates']} across "
          f"{report['summary']['containers_with_dds_candidates']} files; "
          f"possible aligned offsets: "
          f"{report['summary']['possible_pointer_matches']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
