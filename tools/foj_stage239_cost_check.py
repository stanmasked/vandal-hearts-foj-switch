#!/usr/bin/env python3
"""Stage239: fail-closed checks on measured Linux host cost JSON receipts.

No threshold on speedup or claim of Nintendo Switch/NeXium performance.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path

SCHEMA = "foj-stage239-host-threat-cost-v1"
WIDTH = 8
HEIGHT = 6
PASSES = 8
TRIALS = 5
CALLS = WIDTH * HEIGHT * PASSES


def validate_report(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Stage239 report must be an object")
    exact = {
        "schema": SCHEMA,
        "source": "generated-research-tactical-simulation",
        "timing_source": "CLOCK_MONOTONIC",
        "platform": "CI Linux host; not Switch or NeXium",
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
        "switch_fps_measured": False,
        "host_wall_time_not_cpu_cycles": True,
        "grid_width": WIDTH,
        "grid_height": HEIGHT,
        "cursor_passes": PASSES,
        "calls_per_trial": CALLS,
        "trials": TRIALS,
        "baseline_forecast_computations": CALLS,
        "cached_forecast_computations": 1,
        "cached_hits": CALLS - 1,
        "digests_identical": True,
        "hard_performance_pass_threshold": False,
    }
    for key, wanted in exact.items():
        actual = data.get(key)
        if type(actual) is not type(wanted) or actual != wanted:
            raise ValueError(f"Invalid benchmark claim {key}: {actual!r}")
    digest = data.get("digest")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{16}", digest) is None:
        raise ValueError("Missing or invalid forecast checksum")

    medians = {}
    for prefix in ("baseline", "cached"):
        samples = data.get(f"{prefix}_duration_ns")
        if not isinstance(samples, list) or len(samples) != TRIALS:
            raise ValueError(f"{prefix}: missing 5 raw timing samples")
        if any(type(x) is not int or x <= 0 for x in samples):
            raise ValueError(f"{prefix}: nonpositive or noninteger nanoseconds")
        med = statistics.median(samples)
        published = data.get(f"{prefix}_median_ns")
        if type(published) is not int or published != med:
            raise ValueError(f"{prefix}: median differs from raw timings")
        ns_per_call = data.get(f"{prefix}_median_ns_per_call")
        if (type(ns_per_call) is not float or not math.isfinite(ns_per_call) or
            not math.isclose(ns_per_call, med / CALLS, rel_tol=0, abs_tol=0.001)):
            raise ValueError(f"{prefix}: invalid nanoseconds per cursor")
        medians[prefix] = med

    ratio = data.get("observed_host_wall_time_ratio")
    expected = medians["baseline"] / medians["cached"]
    if (type(ratio) is not float or not math.isfinite(ratio) or
        ratio <= 0 or not math.isclose(ratio, expected, rel_tol=0, abs_tol=0.001)):
        raise ValueError("Published wall-clock ratio disagrees with raw medians")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    arguments = parser.parse_args()
    with arguments.report.open(encoding="utf-8") as source:
        data = json.load(source)
    validate_report(data)
    print("Stage239 host timing receipt validated: 5+5 raw trials, "
          "384 forecast calls, identical digests and no Switch FPS claim")


if __name__ == "__main__":
    main()
