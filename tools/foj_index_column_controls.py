#!/usr/bin/env python3
"""Read-only checks for index-like words beside hypothetical DDS pointer tables.

No claimed PS3 material/model schema. A dense 0..N-1 column is only a
numeric pattern; an independently sampled local background supplies an
explicit false-coincidence warning, not a confidence score.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.foj_report_transit_budget import measure_report, read_report

from tools.foj_texture_relations import (
    _read_prefix, _safe_relative_path, MAX_PREFIX_BYTES,
)
from tools.foj_resource_table_hypotheses import SUPPORTED_STRIDES

DEFAULT_PREFIX_BYTES = 65536
MAX_TABLES = 2000
MAX_TABLE_ROWS = 32768
MAX_CONTROL_WINDOWS = 1024


def strict_int(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError("Invalid " + name)
    return value


def _index_pattern(values: list[int]) -> str | None:
    if not values or any(x >= len(values) for x in values):
        return None
    if values == list(range(len(values))):
        return "ascending-zero-based"
    if len(set(values)) == len(values) and set(values) == set(range(len(values))):
        return "zero-based-permutation"
    return None


def _read_words(prefix: bytes, positions: list[int], order: str) -> list[int] | None:
    if any(p < 0 or p % 4 or p + 4 > len(prefix) for p in positions):
        return None
    return [int.from_bytes(prefix[p:p + 4], order) for p in positions]


def _controls(prefix: bytes, start: int, last: int, stride: int,
              count: int, order: str, max_windows: int) -> tuple[int, int]:
    """Sample independent windows outside the entire suspected table."""
    total_starts = max(0, (len(prefix) - 4 - (count - 1) * stride) // 4 + 1)
    step = max(1, (total_starts + max_windows - 1) // max_windows)
    checked = 0
    matches = 0
    for j in range(0, total_starts, step):
        at = j * 4
        end = at + (count - 1) * stride + 4
        # Conservative exclusion: no overlap with original table records.
        if not (end <= start - stride + 4 or at >= last + stride):
            continue
        vals = _read_words(prefix, [at + k * stride for k in range(count)], order)
        if vals is None:
            continue
        checked += 1
        if _index_pattern(vals):
            matches += 1
    return checked, matches


def analyze_index_columns(manifest: dict[str, Any], *, root: Path,
                          prefix_bytes: int = DEFAULT_PREFIX_BYTES,
                          min_entries: int = 4,
                          max_control_windows: int = 256) -> dict[str, Any]:
    measure_report(manifest)
    if not isinstance(manifest, dict) or (
        manifest.get("schema") != "foj-resource-table-hypotheses-v1"
    ):
        raise ValueError("Expected the stage-143 table hypotheses report")
    strict_int(prefix_bytes, "prefix bytes", 4, MAX_PREFIX_BYTES)
    strict_int(min_entries, "minimum rows", 3, 32)
    strict_int(max_control_windows, "control windows", 1, MAX_CONTROL_WINDOWS)
    if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
        raise ValueError("Root must be a non-symlink local directory")
    root = root.resolve()
    input_containers = manifest.get("containers")
    if not isinstance(input_containers, list):
        raise ValueError("Invalid report containers")
    output = []
    seen_paths = set()
    total_tables = 0
    total_rows = 0
    totals = {
        "hypotheses_examined": 0,
        "index_like_single_field": 0,
        "index_like_multiple_fields": 0,
        "index_like_with_control_matches": 0,
        "no_index_like_field": 0,
        "ineligible_short_or_no_secondary_word": 0,
    }
    for container in input_containers:
        if not isinstance(container, dict):
            raise ValueError("Invalid input container")
        rel = str(_safe_relative_path(container.get("relative_path")))
        if rel in seen_paths:
            raise ValueError("Repeated input container")
        seen_paths.add(rel)
        tables = container.get("table_hypotheses")
        if not isinstance(tables, list):
            raise ValueError("Invalid table list")
        total_tables += len(tables)
        if total_tables > MAX_TABLES:
            raise ValueError("Too many table hypotheses")
        validated = []
        for table in tables:
            if not isinstance(table, dict) or table.get("interpretation") != (
                "hypothetical-fixed-stride-offset-table"
            ):
                raise ValueError("Unrecognized table metadata")
            start = strict_int(table.get("start_word_offset"), "start", 0,
                               prefix_bytes - 4)
            stride = table.get("stride_bytes")
            if isinstance(stride, bool) or stride not in SUPPORTED_STRIDES:
                raise ValueError("Invalid table stride")
            count = strict_int(table.get("entry_count"), "row count", 2, 1024)
            total_rows += count
            if total_rows > MAX_TABLE_ROWS:
                raise ValueError("Too many table rows")
            end = start + (count - 1) * stride
            if (end > prefix_bytes - 4 or
                table.get("end_word_offset") != end):
                raise ValueError("Inconsistent table bounds")
            order = table.get("byte_order")
            if order not in ("little", "big"):
                raise ValueError("Unknown pointer byte order")
            dest = table.get("target_dds_offsets")
            if not isinstance(dest, list) or len(dest) != count:
                raise ValueError("Invalid destination count")
            for d in dest:
                strict_int(d, "DDS destination", 128, 0xffffffff)
            if table.get("distinct_dds_targets") != len(set(dest)):
                raise ValueError("Inconsistent distinct destination count")
            validated.append((start, end, stride, count, order))
        if not validated:
            continue
        prefix = _read_prefix(root, _safe_relative_path(rel), prefix_bytes)
        results = []
        for start, end, stride, count, order in validated:
            item: dict[str, Any] = {
                "table_start_word_offset": start,
                "stride_bytes": stride,
                "entry_count": count,
                "byte_order": order,
                "possible_secondary_index_fields": [],
                "independent_control_windows_checked": 0,
                "independent_control_dense_windows": 0,
                "structural_observation": "not-eligible",
            }
            totals["hypotheses_examined"] += 1
            if count >= min_entries and stride >= 8:
                for delta in range(-(stride - 4), stride, 4):
                    if delta == 0:
                        continue
                    positions = [start + delta + i * stride for i in range(count)]
                    values = _read_words(prefix, positions, order)
                    if values is None:
                        continue
                    pattern = _index_pattern(values)
                    if pattern:
                        item["possible_secondary_index_fields"].append({
                            "field_delta_from_pointer_bytes": delta,
                            "pattern": pattern,
                            "distinct_numeric_values": len(values),
                        })
                checked, controls = _controls(
                    prefix, start, end, stride, count, order, max_control_windows)
                item["independent_control_windows_checked"] = checked
                item["independent_control_dense_windows"] = controls
                found = len(item["possible_secondary_index_fields"])
                if found > 1:
                    item["structural_observation"] = "ambiguous-index-like-fields"
                    totals["index_like_multiple_fields"] += 1
                elif found == 1:
                    totals["index_like_single_field"] += 1
                    if controls:
                        item["structural_observation"] = "index-like-with-control-matches"
                        totals["index_like_with_control_matches"] += 1
                    else:
                        item["structural_observation"] = "index-like-unverified"
                else:
                    item["structural_observation"] = "no-index-like-field"
                    totals["no_index_like_field"] += 1
            else:
                totals["ineligible_short_or_no_secondary_word"] += 1
            results.append(item)
        output.append({"relative_path": rel, "examined_tables": results})
    report = {
        "schema": "foj-index-column-observations-v1",
        "source_schema": "foj-resource-table-hypotheses-v1",
        "assessment": "unverified numeric patterns; no FoJ material/model indices confirmed",
        "controls": "sampled-independent-same-stride-zero-based-sequences",
        "max_prefix_bytes_per_file": prefix_bytes,
        "minimum_rows_for_pattern": min_entries,
        "containers": output,
        "summary": {**totals, "model_or_material_mapping_verified": False},
    }

    measure_report(report)
    return report

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tables", type=Path, help="Local stage-143 metadata JSON")
    parser.add_argument("--root", type=Path, required=True,
                        help="Same private local extracted directory")
    parser.add_argument("--output", type=Path, required=True,
                        help="Private metadata-only JSON output")
    parser.add_argument("--min-entries", type=int, default=4)
    parser.add_argument("--control-windows", type=int, default=256)
    parser.add_argument("--prefix-bytes", type=int, default=DEFAULT_PREFIX_BYTES)
    args = parser.parse_args()
    try:
        observations = analyze_index_columns(
            read_report(args.tables),
            root=args.root, prefix_bytes=args.prefix_bytes,
            min_entries=args.min_entries,
            max_control_windows=args.control_windows)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(observations, ensure_ascii=False, indent=2, sort_keys=True) +
        "\n", encoding="utf-8")
    print("Examined hypothetical tables: "
          f"{observations['summary']['hypotheses_examined']}; "
          f"index-like single-field observations: "
          f"{observations['summary']['index_like_single_field']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
