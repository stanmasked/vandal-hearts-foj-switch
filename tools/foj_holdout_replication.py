#!/usr/bin/env python3
"""Compare *disjoint local cohorts* of FoJ DDS metadata, not asset formats.

Accepts stage-145 JSON reports and two separate private directory roots.
Rejects nested/same roots, symlink traversals, shared hardlinked files and
inconsistent report shapes. Structural repetition is NEVER game validation:
neither file-content independence nor genuine PS3 origin can be proven here.
No source pixels, binary records or full file hashes enter the output.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import stat
from typing import Any

from tools.foj_texture_relations import _safe_relative_path
from tools.foj_resource_table_hypotheses import SUPPORTED_STRIDES

MAX_FILES = 20000
MAX_TABLES = 10000
MAX_ROWS = 250000
TRIAGES = {
    "internally-contradicted",
    "insufficient-or-ambiguous",
    "internally-consistent-for-private-review",
}


def _int(value: Any, field: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError("Invalid " + field)
    return value


def _root(path: Path) -> Path:
    if not isinstance(path, Path) or path.is_symlink() or not path.is_dir():
        raise ValueError("Each cohort root must be a real directory")
    return path.resolve()


def _file_identity(root: Path, raw: str) -> tuple[int, int]:
    relative = _safe_relative_path(raw)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink traversal is forbidden")
    try:
        st = cursor.lstat()
    except OSError as exc:
        raise ValueError("Candidate file is absent or unreadable") from exc
    if not stat.S_ISREG(st.st_mode):
        raise ValueError("Candidate must be a regular file")
    return st.st_dev, st.st_ino


def _cohort(report: dict, root: Path) -> tuple[dict[tuple[int, str], Counter], set[tuple[int, int]], dict]:
    if not isinstance(report, dict) or report.get("schema") != (
        "foj-cross-report-consistency-v1"
    ):
        raise ValueError("Expected a stage-145 triage report")
    if report.get("assessment") != (
        "same-source cross-report consistency only; not independent evidence"
    ):
        raise ValueError("Report lineage/assessment is not expected")
    containers = report.get("containers")
    if not isinstance(containers, list) or len(containers) > MAX_FILES:
        raise ValueError("Invalid container list")
    signatures: dict[tuple[int, str], Counter] = defaultdict(Counter)
    identities: set[tuple[int, int]] = set()
    filenames = set()
    observed_tables = 0
    total_rows = 0
    counts: Counter = Counter()
    for container in containers:
        if not isinstance(container, dict):
            raise ValueError("Invalid container")
        relative = str(_safe_relative_path(container.get("relative_path")))
        if relative in filenames:
            raise ValueError("Repeated relative filename")
        filenames.add(relative)
        file_id = _file_identity(root, relative)
        if file_id in identities:
            raise ValueError("One cohort aliases a source file")
        identities.add(file_id)
        tables = container.get("table_observations")
        if not isinstance(tables, list):
            raise ValueError("Invalid observed tables")
        seen = set()
        for table in tables:
            if not isinstance(table, dict):
                raise ValueError("Invalid table observation")
            begin = _int(table.get("table_start_word_offset"), "table start", 0, 0xffffffff)
            stride = table.get("stride_bytes")
            if type(stride) is not int or stride not in SUPPORTED_STRIDES:
                raise ValueError("Unsupported table stride")
            rows = _int(table.get("entry_count"), "entry count", 2, 1024)
            total_rows += rows
            if total_rows > MAX_ROWS:
                raise ValueError("Too many rows")
            order = table.get("byte_order")
            if order not in ("little", "big"):
                raise ValueError("Unexpected byte order")
            key = (begin, stride, rows, order)
            if key in seen:
                raise ValueError("Duplicate table within file")
            seen.add(key)
            matched = _int(table.get("corroborated_pointer_rows"),
                           "corroborated rows", 0, rows)
            outcome = table.get("internal_triage")
            if outcome not in TRIAGES:
                raise ValueError("Unexpected triage result")
            reasons = table.get("reason_codes")
            if not isinstance(reasons, list) or not all(
                isinstance(reason, str) and reason for reason in reasons
            ) or len(reasons) > 32 or len(reasons) != len(set(reasons)):
                raise ValueError("Invalid reason codes")
            if table.get("game_material_or_model_link_proven") is not False:
                raise ValueError("Report incorrectly claims game linkage")
            if outcome == "internally-consistent-for-private-review" and (
                reasons or matched != rows
            ):
                raise ValueError("Internally consistent table has contradictions")
            if outcome != "internally-consistent-for-private-review" and not reasons:
                raise ValueError("Non-consistent table is missing reasons")
            # Ignore absolute file offsets and row count: same schema may
            # occur at different positions and with different-sized tables.
            signature = (stride, order)
            signatures[signature][outcome] += 1
            counts[outcome] += 1
            observed_tables += 1
            if observed_tables > MAX_TABLES:
                raise ValueError("Too many observed tables")
    summary = report.get("summary")
    if not isinstance(summary, dict) or summary.get(
        "foj_resource_format_confirmed"
    ) is not False or summary.get("tables_examined") != observed_tables:
        raise ValueError("Invalid report summary")
    expected = {
        "internally_contradicted": counts["internally-contradicted"],
        "insufficient_or_ambiguous": counts["insufficient-or-ambiguous"],
        "internally_consistent_for_private_review":
            counts["internally-consistent-for-private-review"],
    }
    if any(summary.get(key) != val for key, val in expected.items()):
        raise ValueError("Report summary contradicts observed records")
    return signatures, identities, {
        "source_files": len(filenames), "tables_examined": observed_tables,
        "internally_consistent": counts["internally-consistent-for-private-review"],
    }


def compare_cohorts(baseline: dict, holdout: dict, *,
                    baseline_root: Path, holdout_root: Path,
                    min_consistent_per_cohort: int = 1) -> dict:
    """Describe repeatability, WITHOUT claiming actual independently proven assets."""
    minimum = _int(min_consistent_per_cohort, "minimum consistent samples", 1, 32)
    left_root, right_root = _root(baseline_root), _root(holdout_root)
    if (left_root == right_root or left_root in right_root.parents or
        right_root in left_root.parents):
        raise ValueError("Cohort roots must be distinct and non-nested")
    a, a_ids, a_summary = _cohort(baseline, left_root)
    b, b_ids, b_summary = _cohort(holdout, right_root)
    if a_ids & b_ids:
        raise ValueError("Cohorts share the same underlying file/inode")
    patterns = []
    counts: Counter = Counter()
    for stride, byte_order in sorted(set(a) | set(b)):
        left = a.get((stride, byte_order), Counter())
        right = b.get((stride, byte_order), Counter())
        lc = left["internally-consistent-for-private-review"]
        rc = right["internally-consistent-for-private-review"]
        if lc >= minimum and rc >= minimum:
            label = "repeated-unverified-pattern"
        elif lc >= minimum and right["internally-contradicted"]:
            label = "holdout-contradiction-observed"
        elif lc >= minimum and right["insufficient-or-ambiguous"]:
            label = "holdout-ambiguous"
        elif lc >= minimum and not rc:
            label = "not-reproduced-in-holdout"
        elif rc >= minimum and not lc:
            label = "holdout-only-unverified-pattern"
        else:
            label = "insufficient-consistent-occurrences"
        counts[label] += 1
        patterns.append({
            "stride_bytes": stride, "byte_order": byte_order,
            "baseline_consistent_tables": lc,
            "holdout_consistent_tables": rc,
            "baseline_ambiguous_or_contradicted":
                sum(left.values()) - lc,
            "holdout_ambiguous_or_contradicted":
                sum(right.values()) - rc,
            "replication_observation": label,
            "foj_resource_format_verified": False,
        })
    return {
        "schema": "foj-metadata-holdout-comparison-v1",
        "source_schema": "foj-cross-report-consistency-v1",
        "assessment": ("disjoint path and inode checks only; copied bytes, "
                       "genuine independent provenance and PS3 formats unverified"),
        "baseline": a_summary,
        "holdout": b_summary,
        "minimum_consistent_tables_per_cohort": minimum,
        "patterns": patterns,
        "summary": {
            "patterns_compared": len(patterns),
            "repeated_unverified_patterns":
                counts["repeated-unverified-pattern"],
            "foj_resource_format_verified": False,
            "sample_independence_proven": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True,
                        help="Private stage-145 baseline JSON")
    parser.add_argument("--holdout", type=Path, required=True,
                        help="Private stage-145 holdout JSON")
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--holdout-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="Private metadata-only comparison JSON")
    parser.add_argument("--min-consistent", type=int, default=1)
    args = parser.parse_args()
    try:
        base = json.loads(args.baseline.read_text(encoding="utf-8"))
        held = json.loads(args.holdout.read_text(encoding="utf-8"))
        result = compare_cohorts(
            base, held, baseline_root=args.baseline_root,
            holdout_root=args.holdout_root,
            min_consistent_per_cohort=args.min_consistent)
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print("Compared", result["summary"]["patterns_compared"],
          "structural patterns; none is a verified FoJ resource format.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
