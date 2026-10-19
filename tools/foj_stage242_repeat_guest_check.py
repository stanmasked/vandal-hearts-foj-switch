#!/usr/bin/env python3
"""Stage242: audit 3 independent NeXium guest timing receipts, not FPS.

Each repeat is validated by Stage241's real screenshot checker again, and
binary hashes must agree across the independent NeXium runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage241_render_guest_check import (
    SCHEMA as INPUT_SCHEMA, verify_render_timing,
)

SCHEMA = "foj-stage242-independent-guest-render-repeats-v1"
RUN_IDS = (1, 2, 3)
INPUT_REPORT = "stage241-render-timing-receipt.json"
EXPECTED_FALSE = (
    "guest_frame_latency_measured", "host_wall_time_measured",
    "physical_switch_hardware_tested", "switch_fps_measured",
    "original_ps3_assets_used", "original_foj_ai_verified",
)


def check_receipt(receipt: dict) -> tuple[list[int], float]:
    if not isinstance(receipt, dict):
        raise ValueError("Guest timing receipt is not an object")
    expected = {
        "schema": INPUT_SCHEMA,
        "emulator": "NeXium",
        "actual_guest_screenshots": len(STATES),
        "timing_metric": "32-frame averaged software-render duration",
        "unit": "microseconds",
        "clock": "libnx armGetSystemTick + armTicksToNs",
        "measurement_scope": "foj_iso_render_battle_cached_options only",
        "guest_timer_valid_nonzero_unsaturated": True,
        "cache_transition_sequence_valid": True,
        "cache_guest_proof": "foj-stage238-nexium-threat-cache-guest-v1",
    }
    for key, wanted in expected.items():
        actual = receipt.get(key)
        if type(actual) is not type(wanted) or actual != wanted:
            raise ValueError(f"False or unsupported timing claim {key}: {actual!r}")
    for key in EXPECTED_FALSE:
        if receipt.get(key) is not False:
            raise ValueError(f"Unsupported hardware/FPS/asset claim: {key}")
    states = receipt.get("render_us_by_game_state")
    digests = receipt.get("frame_sha256")
    if not isinstance(states, dict) or set(states) != set(STATES):
        raise ValueError("Missing or extra guest battle states")
    if not isinstance(digests, dict) or set(digests) != set(STATES):
        raise ValueError("Missing or extra actual frame SHA-256")
    raw = []
    for name in STATES:
        value = states[name]
        if type(value) is not int or not 1 <= value < 65535:
            raise ValueError(f"Bad guest software-render microseconds {name}")
        digest = digests[name]
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError(f"Invalid guest screenshot digest {name}")
        raw.append(value)
    if len(set(raw)) < 2 or len(set(digests.values())) < 2:
        raise ValueError("Stale guest timing or static screenshots")
    correct = {
        "min_render_us": min(raw),
        "median_render_us": statistics.median(raw),
        "max_render_us": max(raw),
    }
    for key, wanted in correct.items():
        actual = receipt.get(key)
        if (isinstance(actual, bool) or not isinstance(actual, (int, float))
                or not math.isfinite(actual) or actual != wanted):
            raise ValueError(f"Tampered within-run summary: {key}")
    return raw, statistics.median(raw)


def summarize_reports(reports: dict[int, dict],
                      binary_digests: dict[int, tuple[str, str]]) -> dict:
    if set(reports) != set(RUN_IDS) or set(binary_digests) != set(RUN_IDS):
        raise ValueError("Require exactly three independently identified runs")
    guest_values = {}
    frame_hashes = {}
    medians = {}
    for run_id in RUN_IDS:
        row, med = check_receipt(reports[run_id])
        guest_values[str(run_id)] = dict(zip(STATES, row))
        medians[str(run_id)] = med
        frame_hashes[run_id] = reports[run_id]["frame_sha256"]
    for i, left in enumerate(RUN_IDS):
        for right in RUN_IDS[i + 1:]:
            if frame_hashes[left] == frame_hashes[right]:
                raise ValueError(f"Identical evidence repeated as runs {left}/{right}")
    digests = {}
    for run_id in RUN_IDS:
        hashes = binary_digests[run_id]
        if (not isinstance(hashes, tuple) or len(hashes) != 2 or
                any(not isinstance(v, str) or
                    re.fullmatch(r"[a-f0-9]{64}", v) is None
                    for v in hashes)):
            raise ValueError(f"Missing or invalid NRO/NeXium hash in run {run_id}")
        digests[run_id] = hashes
    if len({item[0] for item in digests.values()}) != 1:
        raise ValueError("Guest executable changed between repeats")
    if len({item[1] for item in digests.values()}) != 1:
        raise ValueError("NeXium archive changed between repeats")

    median_values = list(medians.values())
    across_median = statistics.median(median_values)
    span = max(median_values) - min(median_values)
    return {
        "schema": SCHEMA,
        "emulator": "NeXium",
        "independent_guest_processes": len(RUN_IDS),
        "screenshot_count": len(RUN_IDS) * len(STATES),
        "per_run_scene_render_us": guest_values,
        "per_run_median_render_us": medians,
        "median_of_run_medians_us": across_median,
        "min_run_median_us": min(median_values),
        "max_run_median_us": max(median_values),
        "range_of_run_medians_us": span,
        "relative_range_percent": round(100 * span / across_median, 3),
        "population_cv_percent": round(
            100 * statistics.pstdev(median_values) / across_median, 3),
        "matching_nro_sha256": digests[1][0],
        "matching_nexium_archive_sha256": digests[1][1],
        "all_guest_screenshots_verified_again": True,
        "physical_switch_hardware_tested": False,
        "switch_fps_measured": False,
        "gpu_time_measured": False,
        "full_frame_latency_measured": False,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
        "speedup_or_stability_threshold_enforced": False,
    }


def read_digest(path: Path) -> str:
    chunks = path.read_text(encoding="utf-8").split()
    if not chunks or not re.fullmatch(r"[a-f0-9]{64}", chunks[0]):
        raise ValueError(f"Invalid SHA-256 audit file: {path}")
    return chunks[0]


def audit_artifacts(root: Path) -> dict:
    reports, hashes = {}, {}
    for run_id in RUN_IDS:
        folder = root / f"foj-stage242-repeat-{run_id}"
        paths = tuple(folder / f"cache-{name.replace('_', '-')}.png"
                      for name in STATES)
        report = json.loads((folder / INPUT_REPORT).read_text(encoding="utf-8"))
        # Re-decode the *actual files* to reject a forged/incorrect JSON.
        independently_decoded = verify_render_timing(paths)
        for key in ("render_us_by_game_state", "frame_sha256"):
            if report.get(key) != independently_decoded[key]:
                raise ValueError(f"Run {run_id}: receipt differs from screenshots ({key})")
        for name, path in zip(STATES, paths):
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if report["frame_sha256"][name] != actual:
                raise ValueError(f"Run {run_id}: screenshot SHA mismatch ({name})")
        log = folder / "guest.log"
        if not log.is_file() or log.stat().st_size == 0:
            raise ValueError(f"Run {run_id}: no NeXium execution log")
        reports[run_id] = report
        hashes[run_id] = (
            read_digest(folder / "nro.sha256"),
            read_digest(folder / "nexium-archive.sha256"),
        )
    return summarize_reports(reports, hashes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    result = audit_artifacts(args.artifacts_root)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print("Stage242: verified 3 actual NeXium guest processes, 27 frames; "
          f"run-median range {result['range_of_run_medians_us']} microseconds; "
          f"relative span {result['relative_range_percent']}% (not FPS)")


if __name__ == "__main__":
    main()
