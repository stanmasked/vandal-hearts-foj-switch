#!/usr/bin/env python3
"""Replay an offline DDS metadata report chain using only local JSON.

Re-derives stage-143 tables from stage-142 hypotheses, checks stage-144
observation completeness and internally consistent labels, and re-runs
stage-145 triage. A successful replay is NOT independent evidence of a
PS3 container format, original asset provenance, or Switch rendering.
No source game files are opened; no original data or filenames are output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.foj_evidence_triage import (
    _by_file, _table_id, _uint, triage_reports,
)
from tools.foj_index_column_controls import MAX_CONTROL_WINDOWS
from tools.foj_resource_table_hypotheses import (
    SUPPORTED_STRIDES, infer_tables,
)
from tools.foj_texture_relations import MAX_PREFIX_BYTES

MAX_JSON_BYTES = 128 * 1024 * 1024
INDEX_PATTERNS = ("ascending-zero-based", "zero-based-permutation")


def _require_equal(actual: Any, expected: Any, explanation: str) -> None:
    if actual != expected:
        raise ValueError(explanation)


def _validate_index_replay(tables: dict, indices: dict) -> int:
    """Require one self-consistent observation for every table hypothesis.

    Does not reopen original bytes: the numerical observations themselves
    remain unverified; this catches missing, duplicated, or edited records.
    """
    by_table = _by_file(tables, "foj-resource-table-hypotheses-v1")
    by_index = _by_file(indices, "foj-index-column-observations-v1")
    _require_equal(
        indices.get("source_schema"), tables.get("schema"),
        "Stage-144 source schema does not match stage 143")
    min_rows = _uint(
        indices.get("minimum_rows_for_pattern"), "minimum rows",
        minimum=3, maximum=32)
    prefix = _uint(
        indices.get("max_prefix_bytes_per_file"), "prefix limit",
        minimum=4, maximum=MAX_PREFIX_BYTES)
    if set(by_index) != {name for name, row in by_table.items()
                         if row.get("table_hypotheses")}:
        raise ValueError("Stage-144 file coverage does not match stage 143")

    seen_count = 0
    for name, table_container in by_table.items():
        proposed = table_container.get("table_hypotheses")
        if not isinstance(proposed, list):
            raise ValueError("Malformed stage-143 table list")
        expected_keys = {_table_id(row) for row in proposed}
        if len(expected_keys) != len(proposed):
            raise ValueError("Duplicate stage-143 table identity")
        if not proposed:
            continue
        observed = by_index[name].get("examined_tables")
        if not isinstance(observed, list):
            raise ValueError("Malformed stage-144 observation list")
        actual = {}
        for row in observed:
            key = _table_id(row, observation=True)
            if key in actual:
                raise ValueError("Duplicate stage-144 table observation")
            actual[key] = row
        if set(actual) != expected_keys:
            raise ValueError("Stage-144 observations omit or invent a table")
        for (begin, stride, count, _order), row in actual.items():
            if begin % 4 or begin + (count - 1) * stride + 4 > prefix:
                raise ValueError("Stage-144 table exceeds the scanned prefix")
            fields = row.get("possible_secondary_index_fields")
            if not isinstance(fields, list) or len(fields) > 16:
                raise ValueError("Malformed stage-144 index fields")
            checked = _uint(
                row.get("independent_control_windows_checked"),
                "control windows", maximum=MAX_CONTROL_WINDOWS)
            matches = _uint(
                row.get("independent_control_dense_windows"),
                "control matches", maximum=MAX_CONTROL_WINDOWS)
            if matches > checked:
                raise ValueError("Control matches exceed sampled windows")
            field_deltas = set()
            for field in fields:
                if not isinstance(field, dict):
                    raise ValueError("Malformed index-field record")
                delta = field.get("field_delta_from_pointer_bytes")
                if (type(delta) is not int or delta == 0 or delta % 4 or
                        not -(stride - 4) <= delta < stride):
                    raise ValueError("Invalid relative index-field position")
                if delta in field_deltas:
                    raise ValueError("Duplicate relative index-field position")
                field_deltas.add(delta)
                if field.get("pattern") not in INDEX_PATTERNS:
                    raise ValueError("Unknown stage-144 index pattern")
                if _uint(field.get("distinct_numeric_values"), "index values",
                         minimum=1, maximum=1024) != count:
                    raise ValueError("Index-field distinct count mismatches rows")
            eligible = count >= min_rows and stride >= 8
            if not eligible:
                if fields or matches or checked:
                    raise ValueError("Ineligible stage-144 table has evidence")
                expected = "not-eligible"
            elif len(fields) > 1:
                expected = "ambiguous-index-like-fields"
            elif len(fields) == 1:
                expected = ("index-like-with-control-matches" if matches
                            else "index-like-unverified")
            else:
                expected = "no-index-like-field"
            if row.get("structural_observation") != expected:
                raise ValueError("Stage-144 observation label contradicts fields")
            seen_count += 1
    return seen_count


def audit_replay(layout: dict, tables: dict, indices: dict,
                 triage: dict) -> dict:
    """Verify deterministic JSON-to-JSON lineage; leave source data private."""
    if not all(isinstance(x, dict)
               for x in (layout, tables, indices, triage)):
        raise ValueError("All four reports must be JSON objects")
    minimum = _uint(
        tables.get("minimum_distinct_dds_targets"),
        "stage-143 minimum distinct targets", minimum=2, maximum=16)
    _require_equal(
        tables.get("allowed_strides_bytes"), list(SUPPORTED_STRIDES),
        "Stage-143 supported strides differ from this implementation")
    replay_tables = infer_tables(layout, min_distinct=minimum)
    _require_equal(
        tables, replay_tables,
        "Stage-143 table report does not replay from stage-142 metadata")
    count = _validate_index_replay(tables, indices)
    replay_triage = triage_reports(layout, tables, indices)
    _require_equal(
        triage, replay_triage,
        "Stage-145 triage report does not replay from stages 142-144")
    return {
        "schema": "foj-report-replay-audit-v1",
        "status": "internally-replayed",
        "assessment": ("deterministic JSON report consistency only; "
                       "not independent asset or PS3 format evidence"),
        "summary": {
            "tables_replayed": count,
            "triage_internally_contradicted":
                replay_triage["summary"]["internally_contradicted"],
            "triage_insufficient_or_ambiguous":
                replay_triage["summary"]["insufficient_or_ambiguous"],
            "triage_internally_consistent_for_private_review":
                replay_triage["summary"][
                    "internally_consistent_for_private_review"],
            "original_foj_asset_proven": False,
            "nintendo_switch_runtime_verified": False,
        },
    }


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object member in local report")
        result[key] = value
    return result


def _read_report(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Report must be a regular non-symlink local file")
    size = path.stat().st_size
    if not 2 <= size <= MAX_JSON_BYTES:
        raise ValueError("JSON report size outside permitted bounds")
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=_no_duplicate_keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ("relations", "tables", "indices", "triage"):
        parser.add_argument("--" + label, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="Local aggregate JSON; no source bytes published")
    args = parser.parse_args()
    try:
        report = audit_replay(*(
            _read_report(getattr(args, name))
            for name in ("relations", "tables", "indices", "triage")
        ))
    except (ValueError, OSError, TypeError, KeyError, UnicodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    print("Report replay checked:",
          report["summary"]["tables_replayed"],
          "hypothetical tables; no FoJ format verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
