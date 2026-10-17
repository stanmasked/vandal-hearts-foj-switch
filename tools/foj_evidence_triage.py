#!/usr/bin/env python3
"""Cross-check three *dependent* PS3 DDS metadata reports, not game formats.

All sources ultimately derive from the same candidate scan. Agreement among
them is internal consistency, NEVER independent validation or a confidence
score. No original asset files are opened, decoded or published.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from tools.foj_texture_relations import _safe_relative_path
from tools.foj_resource_table_hypotheses import SUPPORTED_STRIDES

MAX_CONTAINERS = 20000
MAX_TABLES = 10000
MAX_CANDIDATES = 250000
MAX_ROWS = 250000
ENDIANS = ("little", "big")
INDEX_OBSERVATIONS = (
    "not-eligible", "no-index-like-field", "ambiguous-index-like-fields",
    "index-like-with-control-matches", "index-like-unverified",
)


def _uint(value: Any, label: str, *, minimum: int = 0,
          maximum: int = 0xffffffff) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("Invalid " + label)
    return value


def _by_file(report: Any, schema: str) -> dict[str, dict[str, Any]]:
    if not isinstance(report, dict) or report.get("schema") != schema:
        raise ValueError("Unexpected or missing report schema: " + schema)
    containers = report.get("containers")
    if not isinstance(containers, list) or len(containers) > MAX_CONTAINERS:
        raise ValueError("Invalid container list")
    output = {}
    for entry in containers:
        if not isinstance(entry, dict):
            raise ValueError("Invalid container entry")
        relative = str(_safe_relative_path(entry.get("relative_path")))
        if relative in output:
            raise ValueError("Duplicate file in report")
        output[relative] = entry
    return output


def _table_id(row: dict[str, Any], *, observation: bool = False) -> tuple:
    if not isinstance(row, dict):
        raise ValueError("Invalid table row")
    begin = _uint(row.get("table_start_word_offset" if observation else
                          "start_word_offset"), "table start")
    stride = row.get("stride_bytes")
    if type(stride) is not int or stride not in SUPPORTED_STRIDES:
        raise ValueError("Unsupported table stride")
    count = _uint(row.get("entry_count"), "row count", minimum=2, maximum=1024)
    order = row.get("byte_order")
    if order not in ENDIANS:
        raise ValueError("Unknown table endian")
    end = begin + (count - 1) * stride
    if not observation:
        if row.get("end_word_offset") != end or (
            row.get("interpretation") != "hypothetical-fixed-stride-offset-table"
        ):
            raise ValueError("Inconsistent table range")
    return (begin, stride, count, order)


def _candidate_map(entry: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = entry.get("candidates")
    if not isinstance(rows, list) or len(rows) > MAX_CANDIDATES:
        raise ValueError("Invalid candidate records")
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid DDS record")
        at = _uint(row.get("offset"), "DDS offset")
        if at in out:
            raise ValueError("Duplicate DDS candidate")
        refs = row.get("possible_32bit_offset_references")
        if not isinstance(refs, list) or len(refs) > 128:
            raise ValueError("Invalid reference list")
        for ref in refs:
            if not isinstance(ref, dict):
                raise ValueError("Invalid pointer hint")
            _uint(ref.get("word_offset"), "pointer hint position")
            if ref.get("byte_order") not in ENDIANS or (
                ref.get("interpretation") != "possible-file-relative-offset"
            ):
                raise ValueError("Invalid pointer hint type")
        end = row.get("candidate_span_end")
        if end is not None and _uint(end, "DDS payload end") < at + 128:
            raise ValueError("Impossible candidate span")
        next_at = row.get("next_candidate_offset")
        if next_at is not None and _uint(next_at, "next DDS offset") <= at:
            raise ValueError("Invalid next header position")
        out[at] = row
    return out


def triage_reports(layout: dict, tables: dict, indices: dict) -> dict:
    """Reconcile known-size DDS spans, pointer hints and adjacent number fields."""
    rel = _by_file(layout, "foj-texture-layout-hypotheses-v1")
    tab = _by_file(tables, "foj-resource-table-hypotheses-v1")
    idx = _by_file(indices, "foj-index-column-observations-v1")
    if tables.get("input_schema") != layout.get("schema") or (
        indices.get("source_schema") != tables.get("schema")
    ):
        raise ValueError("Broken report lineage")
    if layout.get("pointer_scan") != "first-file-prefix-aligned-uint32-le-be":
        raise ValueError("No stage-142 local pointer scan in report")
    if not set(tab).issubset(rel) or not set(idx).issubset(tab):
        raise ValueError("Reports disagree about container filenames")

    outcomes: list[dict[str, Any]] = []
    counts: Counter = Counter()
    total_rows = 0
    for filename in sorted(tab):
        t_rows = tab[filename].get("table_hypotheses")
        if not isinstance(t_rows, list):
            raise ValueError("Missing table hypotheses")
        observations = idx.get(filename, {}).get("examined_tables", [])
        if not isinstance(observations, list):
            raise ValueError("Invalid observations")
        by_index = {}
        for observation in observations:
            key = _table_id(observation, observation=True)
            if key in by_index:
                raise ValueError("Duplicate index observation")
            by_index[key] = observation
        valid_keys = {_table_id(t) for t in t_rows}
        if not set(by_index).issubset(valid_keys):
            raise ValueError("Index observations refer to unknown table")
        candidates = _candidate_map(rel[filename])
        seen_tables = set()
        grouped_results = []
        for table in t_rows:
            key = _table_id(table)
            if key in seen_tables:
                raise ValueError("Duplicate table hypothesis")
            seen_tables.add(key)
            begin, stride, count, order = key
            total_rows += count
            if total_rows > MAX_ROWS:
                raise ValueError("Too many table rows")
            targets = table.get("target_dds_offsets")
            if not isinstance(targets, list) or len(targets) != count:
                raise ValueError("Missing table destinations")
            for destination in targets:
                _uint(destination, "DDS table destination")
            if table.get("distinct_dds_targets") != len(set(targets)):
                raise ValueError("Incorrect unique destination count")
            reasons = set()
            corroborated = 0
            for i, destination in enumerate(targets):
                candidate = candidates.get(destination)
                if candidate is None:
                    reasons.add("missing-dds-header-candidate")
                    continue
                word = begin + i * stride
                if any(ref["word_offset"] == word and
                       ref["byte_order"] == order for ref in
                       candidate["possible_32bit_offset_references"]):
                    corroborated += 1
                else:
                    reasons.add("pointer-hint-not-corroborated")
                end = candidate.get("candidate_span_end")
                if end is None:
                    reasons.add("unknown-dds-payload-size")
                else:
                    next_at = candidate.get("next_candidate_offset")
                    if next_at is not None and end > next_at:
                        reasons.add("overlapping-dds-candidate-spans")

            observation = by_index.get(key)
            if observation is None:
                reasons.add("missing-index-observation")
            else:
                status = observation.get("structural_observation")
                if status not in INDEX_OBSERVATIONS:
                    raise ValueError("Unexpected index observation type")
                matches = _uint(observation.get(
                    "independent_control_dense_windows"),
                    "control matches", maximum=1048576)
                checked = _uint(observation.get(
                    "independent_control_windows_checked"),
                    "control samples", maximum=1048576)
                fields = observation.get("possible_secondary_index_fields")
                if not isinstance(fields, list) or len(fields) > 16:
                    raise ValueError("Invalid secondary field list")
                if matches > checked:
                    raise ValueError("Controls exceed sampled windows")
                if matches:
                    reasons.add("similar-pattern-found-in-controls")
                if len(fields) > 1 or status == "ambiguous-index-like-fields":
                    reasons.add("ambiguous-secondary-index-field")
                elif len(fields) == 0:
                    reasons.add("no-secondary-index-pattern")
                if status in ("not-eligible", "no-index-like-field"):
                    reasons.add("ineligible-or-negative-index-observation")
                if len(fields) == 1 and status not in (
                    "index-like-unverified", "index-like-with-control-matches"
                ):
                    raise ValueError("Index observation conflicts with field count")
                if status == "index-like-with-control-matches" and matches == 0:
                    raise ValueError("Control-match label contradicts count")

            hard = {"missing-dds-header-candidate",
                    "pointer-hint-not-corroborated",
                    "overlapping-dds-candidate-spans"}
            if reasons & hard:
                result = "internally-contradicted"
            elif reasons:
                result = "insufficient-or-ambiguous"
            else:
                result = "internally-consistent-for-private-review"
            counts[result] += 1
            grouped_results.append({
                "table_start_word_offset": begin,
                "stride_bytes": stride,
                "entry_count": count,
                "byte_order": order,
                "corroborated_pointer_rows": corroborated,
                "internal_triage": result,
                "reason_codes": sorted(reasons),
                "game_material_or_model_link_proven": False,
            })
        if grouped_results:
            outcomes.append({
                "relative_path": filename,
                "table_observations": grouped_results,
            })
    return {
        "schema": "foj-cross-report-consistency-v1",
        "inputs": [
            "foj-texture-layout-hypotheses-v1",
            "foj-resource-table-hypotheses-v1",
            "foj-index-column-observations-v1",
        ],
        "assessment": "same-source cross-report consistency only; not independent evidence",
        "containers": outcomes,
        "summary": {
            "tables_examined": sum(counts.values()),
            "internally_contradicted": counts["internally-contradicted"],
            "insufficient_or_ambiguous": counts["insufficient-or-ambiguous"],
            "internally_consistent_for_private_review":
                counts["internally-consistent-for-private-review"],
            "foj_resource_format_confirmed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relations", type=Path, required=True,
                        help="Local stage-142 layout/pointer JSON")
    parser.add_argument("--tables", type=Path, required=True,
                        help="Local stage-143 table JSON")
    parser.add_argument("--indices", type=Path, required=True,
                        help="Local stage-144 numeric field observations JSON")
    parser.add_argument("--output", type=Path, required=True,
                        help="Local metadata-only triage JSON")
    args = parser.parse_args()
    try:
        output = triage_reports(*[
            json.loads(path.read_text(encoding="utf-8"))
            for path in (args.relations, args.tables, args.indices)
        ])
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Cross-report tables checked:",
          output["summary"]["tables_examined"],
          "(not confirmed FoJ resource links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
