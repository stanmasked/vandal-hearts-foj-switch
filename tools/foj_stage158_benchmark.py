#!/usr/bin/env python3
"""Reproducible, generated-only FoJ DDS research performance experiment.

Measures metadata processing rather than proprietary resources or hardware
performance. Durations and Python allocation peaks vary between runners.
No user-owned files, private paths, hostnames or input data are reported.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import struct
import sys
import tempfile
import time
import tracemalloc
from typing import Any

from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import _candidate_runs

PROFILES = {
    "smoke": (32, 128),
    "standard": (128, 512),
    "stress": (512, 2048),
}
MAX_REPEATS = 5
DDS_HEADER_BYTES = 128


def generated_case(directory: Path, candidates: int) -> tuple[dict[str, Any], int]:
    """Create invented candidate offsets and a deterministic local file.

    This does not claim to reconstruct actual FoJ assets. DDS headers and
    pointer words are invented only to exercise metadata research code.
    """
    if type(candidates) is not int or not 1 <= candidates <= 2048:
        raise ValueError("Invalid generated candidate count")
    required = 512 + (candidates - 1) * 128 + DDS_HEADER_BYTES
    prefix_bytes = max(65536, 1 << (required - 1).bit_length())
    directory.mkdir(parents=True, exist_ok=True)
    data = bytearray(b"\xff" * prefix_bytes)
    offsets = [512 + 128 * i for i in range(candidates)]
    for position in offsets:
        data[position:position + 4] = b"DDS "
        struct.pack_into("<I", data, position + 4, 124)
        struct.pack_into("<I", data, position + 76, 32)
        struct.pack_into("<I", data, position + 12, 8)
        struct.pack_into("<I", data, position + 16, 8)
        struct.pack_into("<I", data, position + 28, 1)
        struct.pack_into("<I", data, position + 80, 4)
        data[position + 84:position + 88] = b"DXT1"
    for slot, target in enumerate(offsets[:3]):
        struct.pack_into("<I", data, slot * 4, target)
    (directory / "generated.bin").write_bytes(data)
    manifest = {
        "schema": "foj-texture-candidates-v1",
        "candidates": [
            {
                "relative_path": "generated.bin",
                "offset": offset,
                "format_candidate": "BC1/DXT1",
                "expected_payload_bytes": 0,
                "payload_check": "additional-bytes-after-declared-mips",
            } for offset in offsets
        ],
    }
    return manifest, prefix_bytes


def generated_runs(groups: int) -> list[tuple[int, int]]:
    """Generate separated three-row numeric patterns, not game pointers."""
    if type(groups) is not int or not 1 <= groups <= 2048:
        raise ValueError("Invalid generated table group count")
    return [(group * 64 + delta, 512 + group * 100 + delta)
            for group in range(groups) for delta in (0, 4, 8)]


def _sample(task, repeats: int, count_records) -> dict[str, float | int]:
    """Median elapsed time and peak traced Python allocation, no thresholds."""
    elapsed = []
    peaks = []
    for _ in range(repeats):
        tracemalloc.start()
        try:
            started = time.perf_counter_ns()
            output = task()
            elapsed.append((time.perf_counter_ns() - started) / 1_000_000)
            peaks.append(tracemalloc.get_traced_memory()[1] / 1024)
        finally:
            tracemalloc.stop()
        records = count_records(output)
    return {
        "median_elapsed_ms": round(statistics.median(elapsed), 3),
        "peak_traced_kib": round(max(peaks), 1),
        "observed_records": records,
    }


def benchmark(*, profile: str = "smoke", repeats: int = 1) -> dict[str, Any]:
    if profile not in PROFILES or type(repeats) is not int or not 1 <= repeats <= MAX_REPEATS:
        raise ValueError("Invalid synthetic benchmark configuration")
    records = []
    with tempfile.TemporaryDirectory(prefix="foj-stage158-generated-") as tmp:
        root = Path(tmp)
        for size in PROFILES[profile]:
            directory = root / f"case-{size}"
            manifest, prefix_bytes = generated_case(directory, size)
            relation = _sample(
                lambda: build_relations(manifest, root=directory,
                                        prefix_bytes=prefix_bytes),
                repeats,
                lambda report: report["summary"]["dds_candidates"],
            )
            if relation["observed_records"] != size:
                raise ValueError("Synthetic relation benchmark incomplete")
            records.append({
                "scenario": "dds-prefix-relations",
                "input_candidates": size,
                "prefix_bytes": prefix_bytes,
                **relation,
            })
            points = generated_runs(size)
            tables = _sample(
                lambda: _candidate_runs(points, min_distinct=3),
                repeats, len,
            )
            if tables["observed_records"] != size:
                raise ValueError("Synthetic table benchmark incomplete")
            records.append({
                "scenario": "hypothetical-table-runs",
                "input_pointer_observations": len(points),
                **tables,
            })
    return {
        "schema": "foj-stage158-synthetic-performance-v1",
        "provenance": "invented-metadata-and-generated-bytes-only",
        "profile": profile,
        "repeats": repeats,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "measurements": records,
        "interpretation": (
            "host-dependent observations, not speedup guarantees, "
            "CI pass/fail thresholds or original FoJ texture evidence"
        ),
        "original_foj_assets_verified": False,
        "switch_hardware_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="smoke")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output", type=Path,
                        help="Optional NEW local JSON report, outside source tree")
    args = parser.parse_args()
    try:
        report = benchmark(profile=args.profile, repeats=args.repeats)
    except ValueError as exc:
        parser.error(str(exc))
    if args.output is not None:
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, sort_keys=True,
                          ensure_ascii=False)
                stream.write("\n")
        except FileExistsError:
            parser.error("Benchmark output must be a new file")
    for item in report["measurements"]:
        print(item["scenario"], item.get("input_candidates",
              item.get("input_pointer_observations")), "records:",
              item["observed_records"], "median_ms:",
              item["median_elapsed_ms"], "peak_traced_kib:",
              item["peak_traced_kib"])
    print("Generated-only benchmark; no native Switch runtime measured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
