#!/usr/bin/env python3
"""Deterministic synthetic stress matrix for FoJ DDS metadata tools.

Checks how previously defined *heuristic* labels change under perturbed
record counts, strides, byte order, index fields and control decoys.
Original PS3 resources are NOT processed, identified, copied or uploaded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import tempfile
from typing import Any

from tools.foj_texture_probe import inventory
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import infer_tables
from tools.foj_index_column_controls import analyze_index_columns
from tools.foj_evidence_triage import triage_reports
from tools.foj_holdout_replication import compare_cohorts

FILE_BYTES = 16384
DDS_BYTES = 160
PREFIX_BYTES = FILE_BYTES
CONTROLS = 1024

# Preset outcomes are regression expectations, not claims about real PS3 data.
CASES = (
    ("more-records", (4, 8, "little", "ascending", False),
     (8, 8, "little", "ascending", False),
     "repeated-unverified-pattern"),
    ("endian-variation", (4, 8, "little", "ascending", False),
     (4, 8, "big", "ascending", False),
     "not-reproduced-in-holdout"),
    ("stride-variation", (4, 8, "little", "ascending", False),
     (4, 16, "little", "ascending", False),
     "not-reproduced-in-holdout"),
    ("permuted-indices", (6, 16, "big", "ascending", False),
     (6, 16, "big", "permuted", False),
     "repeated-unverified-pattern"),
    ("short-tables", (3, 8, "little", "ascending", False),
     (3, 8, "little", "ascending", False),
     "insufficient-consistent-occurrences"),
    ("negative-control-decoy", (4, 8, "little", "ascending", False),
     (4, 8, "little", "ascending", True),
     "holdout-ambiguous"),
    ("repeated-index-values", (4, 8, "little", "ascending", False),
     (4, 8, "little", "repeated", False),
     "holdout-ambiguous"),
)


def _dds() -> bytes:
    b = bytearray(DDS_BYTES)
    b[:4] = b"DDS "
    for pos, value in ((4, 124), (8, 0x81007), (12, 8), (16, 8),
                       (20, 32), (28, 1), (76, 32), (80, 4),
                       (84, 0x31545844), (108, 0x1000)):
        struct.pack_into("<I", b, pos, value)
    return bytes(b)


def synthetic_sample(root: Path, spec: tuple) -> None:
    """Invent a DDS container with bounded offsets; NEVER use PS3 bytes."""
    if not isinstance(spec, tuple) or len(spec) != 5:
        raise ValueError("Invalid synthetic spec")
    rows, stride, order, index_mode, decoy = spec
    if type(rows) is not int or not 3 <= rows <= 8:
        raise ValueError("Synthetic rows must be 3..8")
    if stride not in (8, 16) or order not in ("little", "big"):
        raise ValueError("Unsupported synthetic stride or byte order")
    if index_mode not in ("ascending", "permuted", "repeated") or type(decoy) is not bool:
        raise ValueError("Unsupported synthetic index mode / decoy")
    raw = bytearray(b"\xff" * FILE_BYTES)
    for i in range(rows):
        offset = 2048 + 256 * i
        raw[offset:offset + DDS_BYTES] = _dds()
        pointer_at = 128 + stride * i
        raw[pointer_at:pointer_at + 4] = offset.to_bytes(4, order)
        index = (i * (rows - 1)) % rows if index_mode == "permuted" else (
            0 if index_mode == "repeated" else i)
        # For rows=6, (rows-1) is coprime to rows, giving a full permutation.
        raw[pointer_at + 4:pointer_at + 8] = index.to_bytes(4, order)
    if decoy:
        for i in range(rows):
            pos = 12000 + stride * i
            raw[pos:pos + 4] = i.to_bytes(4, order)
    root.mkdir(parents=True, exist_ok=True)
    (root / "synthetic.bin").write_bytes(raw)


def pipeline(root: Path) -> dict[str, Any]:
    scan = inventory(root)
    layout = build_relations(scan, root=root, prefix_bytes=PREFIX_BYTES)
    table = infer_tables(layout)
    index = analyze_index_columns(
        table, root=root, prefix_bytes=PREFIX_BYTES,
        max_control_windows=CONTROLS)
    return triage_reports(layout, table, index)


def run_stability_matrix(cases: tuple = CASES) -> dict[str, Any]:
    if not isinstance(cases, tuple) or not 1 <= len(cases) <= 32:
        raise ValueError("Expected 1..32 predetermined synthetic scenarios")
    experiments = []
    ids = set()
    for name, base, held, expected in cases:
        if not isinstance(name, str) or not name or name in ids:
            raise ValueError("Duplicate or invalid scenario name")
        ids.add(name)
        with tempfile.TemporaryDirectory(prefix="foj-stability-") as tmp:
            a, b = Path(tmp) / "baseline", Path(tmp) / "holdout"
            synthetic_sample(a, base)
            synthetic_sample(b, held)
            baseline = pipeline(a)
            holdout = pipeline(b)
            comparison = compare_cohorts(
                baseline, holdout, baseline_root=a, holdout_root=b)
            shape = (base[1], base[2])
            matches = [p for p in comparison["patterns"]
                       if (p["stride_bytes"], p["byte_order"]) == shape]
            if len(matches) != 1:
                actual = "missing-or-ambiguous-baseline-shape"
            else:
                actual = matches[0]["replication_observation"]
            experiments.append({
                "scenario": name,
                "baseline_row_count": base[0],
                "holdout_row_count": held[0],
                "baseline_stride": base[1],
                "holdout_stride": held[1],
                "baseline_byte_order": base[2],
                "holdout_byte_order": held[2],
                "baseline_tables": baseline["summary"]["tables_examined"],
                "holdout_tables": holdout["summary"]["tables_examined"],
                "expected_observation": expected,
                "actual_observation": actual,
                "matches_expectation": actual == expected,
            })
    return {
        "schema": "foj-synthetic-stability-matrix-v1",
        "synthetic_only": True,
        "game_format_verified": False,
        "note": ("Regression classifications depend on the current "
                 "heuristics and deterministic invented input bytes."),
        "cases": experiments,
        "summary": {
            "total_cases": len(experiments),
            "matched_expectations": sum(x["matches_expectation"]
                                        for x in experiments),
            "unexpected_cases": sum(not x["matches_expectation"]
                                    for x in experiments),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="Local aggregate JSON (never actual game data)")
    args = parser.parse_args()
    report = run_stability_matrix()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    print("Synthetic stability scenarios:", report["summary"]["total_cases"],
          "; expected:", report["summary"]["matched_expectations"],
          "; regressions:", report["summary"]["unexpected_cases"])
    return 0 if report["summary"]["unexpected_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
