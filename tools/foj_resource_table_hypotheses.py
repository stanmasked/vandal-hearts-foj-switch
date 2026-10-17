#!/usr/bin/env python3
"""Find *hypothetical* fixed-stride tables of DDS offsets in private metadata.

Consumes only the stage-142 local JSON report (no PS3 binary access).
Even aligned, sequential pointer coincidences are not verified containers,
material links, texture indexes, model references or PS3 format support.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from tools.foj_report_transit_budget import measure_report, read_report

from tools.foj_texture_relations import _safe_relative_path, MAX_PREFIX_BYTES

SUPPORTED_STRIDES = (4, 8, 12, 16, 24, 32)
DEFAULT_MIN_DISTINCT = 3
MAX_INPUT_CONTAINERS = 20000
MAX_TOTAL_CANDIDATES = 250000
MAX_TOTAL_POINTER_HINTS = 500000
MAX_TABLES = 10000


def _integer(value: Any, label: str, *, low: int = 0, high: int = 0xffffffff) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError("Invalid " + label)
    return value


def _validated_references(manifest: dict[str, Any]) -> dict[str, dict[str, list[tuple[int, int]]]]:
    if manifest.get("schema") != "foj-texture-layout-hypotheses-v1":
        raise ValueError("Expected a stage-142 layout-hypotheses report")
    if manifest.get("pointer_scan") != "first-file-prefix-aligned-uint32-le-be":
        raise ValueError("Stage-142 report must include opt-in pointer hints")
    prefix = _integer(manifest.get("pointer_prefix_bytes"), "pointer prefix",
                      low=4, high=MAX_PREFIX_BYTES)
    containers = manifest.get("containers")
    if not isinstance(containers, list) or len(containers) > MAX_INPUT_CONTAINERS:
        raise ValueError("Invalid or oversized container list")
    grouped: dict[str, dict[str, list[tuple[int, int]]]] = {}
    total_candidates = 0
    total_hints = 0
    for container in containers:
        if not isinstance(container, dict):
            raise ValueError("Invalid container")
        relative = str(_safe_relative_path(container.get("relative_path")))
        if relative in grouped:
            raise ValueError("Duplicate container in report")
        candidates = container.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError("Invalid candidate list")
        total_candidates += len(candidates)
        if total_candidates > MAX_TOTAL_CANDIDATES:
            raise ValueError("Too many DDS candidates")
        order_map: dict[str, list[tuple[int, int]]] = {
            "little": [], "big": []}
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("Invalid candidate")
            offset = _integer(candidate.get("offset"), "DDS target offset", low=128)
            refs = candidate.get("possible_32bit_offset_references")
            if not isinstance(refs, list) or len(refs) > 128:
                raise ValueError("Invalid candidate reference hints")
            total_hints += len(refs)
            if total_hints > MAX_TOTAL_POINTER_HINTS:
                raise ValueError("Too many pointer hints")
            for ref in refs:
                if not isinstance(ref, dict):
                    raise ValueError("Invalid reference hint")
                pos = _integer(ref.get("word_offset"), "reference word offset",
                               high=prefix - 4)
                order = ref.get("byte_order")
                if pos % 4 or order not in ("little", "big") or (
                    ref.get("interpretation") != "possible-file-relative-offset"
                ):
                    raise ValueError("Unexpected pointer hint")
                order_map[order].append((pos, offset))
        grouped[relative] = order_map
    return grouped


def _candidate_runs(points: list[tuple[int, int]], *, min_distinct: int) -> list[dict[str, Any]]:
    """Report maximal fixed-stride runs with distinct DDS destinations.

    A byte position that ambiguously maps to multiple candidate targets
    for the same endianness is omitted rather than arbitrarily selected.
    """
    targets: dict[int, set[int]] = defaultdict(set)
    for pos, offset in points:
        targets[pos].add(offset)
    safe = {p: next(iter(t)) for p, t in targets.items() if len(t) == 1}
    possible = []
    for stride in SUPPORTED_STRIDES:
        for start in sorted(safe):
            if start - stride in safe:
                continue  # Only the first entry of a maximal run.
            positions = []
            at = start
            while at in safe:
                positions.append(at)
                at += stride
            dest = [safe[p] for p in positions]
            if len(positions) < min_distinct or len(set(dest)) < min_distinct:
                continue
            possible.append({
                "start_word_offset": start,
                "end_word_offset": positions[-1],
                "stride_bytes": stride,
                "entry_count": len(positions),
                "distinct_dds_targets": len(set(dest)),
                "target_dds_offsets": dest,
                "_positions": positions,
            })
    # A long stride-4 sequence otherwise produces many spurious alternate
    # stride-8/12 sub-tables. Retain only maximal, non-subsumed hypotheses.
    possible.sort(key=lambda t: (-t["entry_count"], t["stride_bytes"],
                                 t["start_word_offset"]))
    accepted = []
    for run in possible:
        positions = set(run["_positions"])
        if any(positions.issubset(set(prev["_positions"])) for prev in accepted):
            continue
        accepted.append(run)
    accepted.sort(key=lambda t: (t["start_word_offset"], t["stride_bytes"],
                                 -t["entry_count"]))
    for run in accepted:
        del run["_positions"]
    return accepted


def infer_tables(manifest: dict[str, Any], *, min_distinct: int = DEFAULT_MIN_DISTINCT,
                 max_tables: int = MAX_TABLES) -> dict[str, Any]:
    measure_report(manifest)
    """Derive strictly metadata-only candidate pointer table patterns."""
    _integer(min_distinct, "minimum distinct targets", low=2, high=16)
    _integer(max_tables, "maximum tables", low=1, high=MAX_TABLES)
    grouped = _validated_references(manifest)
    output = []
    total = 0
    for relative in sorted(grouped):
        by_order = grouped[relative]
        records = []
        for order in ("little", "big"):
            for run in _candidate_runs(by_order[order], min_distinct=min_distinct):
                run["byte_order"] = order
                run["interpretation"] = "hypothetical-fixed-stride-offset-table"
                records.append(run)
        records.sort(key=lambda x: (x["start_word_offset"],
                                    x["byte_order"], x["stride_bytes"]))
        if len(records) + total > max_tables:
            raise ValueError("Maximum table hypotheses exceeded")
        total += len(records)
        if records:
            output.append({"relative_path": relative, "table_hypotheses": records})
    report = {
        "schema": "foj-resource-table-hypotheses-v1",
        "input_schema": "foj-texture-layout-hypotheses-v1",
        "evidence": "numeric-coincidence-only; no confirmed FoJ resource mapping",
        "allowed_strides_bytes": list(SUPPORTED_STRIDES),
        "minimum_distinct_dds_targets": min_distinct,
        "containers": output,
        "summary": {
            "files_with_hypothetical_tables": len(output),
            "table_hypotheses": total,
            "no_model_or_material_mapping_established": True,
        },
    }

    measure_report(report)
    return report

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("relations", type=Path,
                        help="Local stage-142 report generated WITH --root")
    parser.add_argument("--output", required=True, type=Path,
                        help="Local JSON; never transmitted automatically")
    parser.add_argument("--min-distinct", type=int, default=DEFAULT_MIN_DISTINCT,
                        help="Require at least 2 distinct target DDS offsets")
    args = parser.parse_args()
    try:
        report = infer_tables(
            read_report(args.relations),
            min_distinct=args.min_distinct)
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print("Hypothetical pointer tables: "
          f"{report['summary']['table_hypotheses']} across "
          f"{report['summary']['files_with_hypothetical_tables']} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
