#!/usr/bin/env python3
"""Privacy-preserving cProfile diagnostics on invented FoJ DDS metadata.

Profiles only deterministic generated workloads. Reports include a fixed,
allowlisted set of source-code phase labels, never Python source paths,
untrusted filenames, source bytes, tracebacks or live user assets.
Timing is diagnostic and must never become a CI pass/fail threshold.
"""
from __future__ import annotations

import argparse
import cProfile
import json
from pathlib import Path
import pstats
import statistics
import sys
import tempfile
import time
from typing import Any, Callable

from tools.foj_stage158_benchmark import PROFILES, generated_case, generated_runs
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import infer_tables

MAX_REPEATS = 3
MAX_PHASES = 8

# Keys refer only to pre-reviewed internal functions. A profiler's raw
# filenames/line numbers/call graphs are never serialized or printed.
SAFE_PHASES = {
    "dds-prefix-relations": {
        ("foj_texture_relations.py", "build_relations"): "relation-analysis",
        ("foj_texture_relations.py", "_merged_candidate_spans"): "dds-range-index",
        ("foj_texture_relations.py", "_read_prefix"): "prefix-request",
        ("foj_fd_bound_reader.py", "read_bounded_prefix"): "prefix-double-read",
        ("foj_report_transit_budget.py", "measure_report"): "json-budget-check",
    },
    "hypothetical-table-inference": {
        ("foj_resource_table_hypotheses.py", "infer_tables"): "table-analysis",
        ("foj_resource_table_hypotheses.py", "_validated_references"): "pointer-validation",
        ("foj_resource_table_hypotheses.py", "_candidate_runs"): "table-run-search",
        ("foj_report_transit_budget.py", "measure_report"): "json-budget-check",
    },
}


def generated_table_manifest(groups: int) -> dict[str, Any]:
    """Build stage-142-shaped numeric hypotheses from invented positions."""
    points = generated_runs(groups)
    return {
        "schema": "foj-texture-layout-hypotheses-v1",
        "pointer_scan": "first-file-prefix-aligned-uint32-le-be",
        "pointer_prefix_bytes": 1048576,
        "containers": [{
            "relative_path": "generated.bin",
            "candidates": [{
                "offset": dest,
                "possible_32bit_offset_references": [{
                    "word_offset": pos,
                    "byte_order": "little",
                    "interpretation": "possible-file-relative-offset",
                }],
            } for pos, dest in points],
        }],
    }


def _profile_once(workload: str, task: Callable[[], Any],
                  expected_count: int, count_records: Callable[[Any], int],
                  max_phases: int) -> dict[str, Any]:
    """Take one cProfile measurement with only allowlisted output fields."""
    profile = cProfile.Profile()
    started = time.perf_counter_ns()
    result = profile.runcall(task)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    if count_records(result) != expected_count:
        raise ValueError("Synthetic profiling workload was incomplete")
    stats = pstats.Stats(profile)
    phases = []
    allow = SAFE_PHASES[workload]
    for (filename, _line, function), (primitive, total_calls, self_s,
                                      cumulative_s, _callers) in stats.stats.items():
        label = allow.get((Path(filename).name, function))
        if label is None:
            continue
        phases.append({
            "phase": label,
            "primitive_calls": primitive,
            "total_calls": total_calls,
            "self_cpu_ms": round(self_s * 1000, 3),
            "cumulative_cpu_ms": round(cumulative_s * 1000, 3),
        })
    phases.sort(key=lambda row: (-row["cumulative_cpu_ms"], row["phase"]))
    if not phases:
        raise ValueError("No expected profiling phases were observed")
    return {
        "wall_elapsed_ms": round(elapsed_ms, 3),
        "profiled_cpu_ms": round(stats.total_tt * 1000, 3),
        "observed_records": expected_count,
        "phases": phases[:max_phases],
    }


def _measure(workload: str, task: Callable[[], Any], expected: int,
             counter: Callable[[Any], int], repeats: int,
             top_phases: int) -> dict[str, Any]:
    elapsed: list[float] = []
    cpu: list[float] = []
    phase_runs: dict[str, list[dict[str, Any]]] = {}
    for _ in range(repeats):
        result = _profile_once(workload, task, expected, counter, top_phases)
        elapsed.append(result["wall_elapsed_ms"])
        cpu.append(result["profiled_cpu_ms"])
        for phase in result["phases"]:
            phase_runs.setdefault(phase["phase"], []).append(phase)
    phases = []
    for label, measurements in phase_runs.items():
        if len(measurements) != repeats:
            raise ValueError("Inconsistent synthetic profiling phase coverage")
        phases.append({
            "phase": label,
            "primitive_calls": measurements[0]["primitive_calls"],
            "total_calls": measurements[0]["total_calls"],
            "median_self_cpu_ms": round(statistics.median(
                x["self_cpu_ms"] for x in measurements), 3),
            "median_cumulative_cpu_ms": round(statistics.median(
                x["cumulative_cpu_ms"] for x in measurements), 3),
        })
    phases.sort(key=lambda row: (-row["median_cumulative_cpu_ms"], row["phase"]))
    return {
        "observed_records": expected,
        "median_wall_elapsed_ms": round(statistics.median(elapsed), 3),
        "median_profiled_cpu_ms": round(statistics.median(cpu), 3),
        "phases": phases,
    }


def profile_synthetic(*, profile: str = "smoke", repeats: int = 1,
                      top_phases: int = MAX_PHASES) -> dict[str, Any]:
    if (profile not in PROFILES or type(repeats) is not int or
            not 1 <= repeats <= MAX_REPEATS or
            type(top_phases) is not int or
            not 1 <= top_phases <= MAX_PHASES):
        raise ValueError("Invalid synthetic profiling configuration")
    measurements = []
    with tempfile.TemporaryDirectory(prefix="foj-stage159-generated-") as tmp:
        for size in PROFILES[profile]:
            directory = Path(tmp) / f"fixture-{size}"
            manifest, prefix_bytes = generated_case(directory, size)
            relation = _measure(
                "dds-prefix-relations",
                lambda: build_relations(
                    manifest, root=directory, prefix_bytes=prefix_bytes),
                size, lambda result: result["summary"]["dds_candidates"],
                repeats, top_phases,
            )
            measurements.append({
                "scenario": "dds-prefix-relations",
                "candidate_count": size,
                "prefix_bytes": prefix_bytes,
                **relation,
            })
            hypothetical = generated_table_manifest(size)
            table = _measure(
                "hypothetical-table-inference",
                lambda: infer_tables(hypothetical),
                size, lambda result: result["summary"]["table_hypotheses"],
                repeats, top_phases,
            )
            measurements.append({
                "scenario": "hypothetical-table-inference",
                "pointer_observations": 3 * size,
                **table,
            })
    return {
        "schema": "foj-stage159-synthetic-hotspots-v1",
        "provenance": "generated-only",
        "profile": profile,
        "repeats": repeats,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "observations": measurements,
        "interpretation": (
            "cProfile phase timings include nested work; cumulative values "
            "overlap and cannot be summed. Host-dependent diagnostic only."
        ),
        "original_foj_assets_verified": False,
        "switch_hardware_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="smoke")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--top-phases", type=int, default=MAX_PHASES)
    parser.add_argument("--output", type=Path,
                        help="Optional NEW local JSON output; never uploaded")
    args = parser.parse_args()
    try:
        result = profile_synthetic(
            profile=args.profile, repeats=args.repeats,
            top_phases=args.top_phases)
    except ValueError as exc:
        parser.error(str(exc))
    if args.output is not None:
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, sort_keys=True,
                          ensure_ascii=False, allow_nan=False)
                stream.write("\n")
        except FileExistsError:
            parser.error("Profiling output must be a new file")
    for item in result["observations"]:
        leaders = ", ".join(
            x["phase"] + "=" + str(x["median_cumulative_cpu_ms"]) + "ms"
            for x in item["phases"][:3])
        print(item["scenario"], item["observed_records"], "records;",
              "median_wall_ms", item["median_wall_elapsed_ms"],
              "phases:", leaders)
    print("Generated-only profiling; no original PS3 or Switch runtime evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
