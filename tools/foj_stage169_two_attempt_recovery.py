#!/usr/bin/env python3
"""Strict, private two-attempt FoJ CPU boot recovery comparison.

No hardware connection, device attestation, GPU telemetry, screenshots,
user paths, proprietary game data or automatic proof of real recovery.
Reads exactly TWO explicitly named, already copied local boot logs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.foj_stage168_boot_journal_audit import (
    LINE, STAGES, invalid, parse_journal, read_journal,
)

SCHEMA = "foj-stage169-two-attempt-cpu-recovery-v1"


def _events(data: bytes) -> list[tuple[int, int, int, int]]:
    """Require the exact C producer's enter -> ready/failed -> next sequence."""
    # Stage 168's parser guards the line format, byte bound, monotonic
    # frame counter and one session. This second pass checks the stricter
    # state machine before reporting comparisons as meaningful.
    parse_journal(data)
    records: list[tuple[int, int, int, int]] = []
    prior_stage = 0
    stage_has_outcome = False
    exited = False
    for row in data.splitlines(keepends=True):
        match = LINE.fullmatch(row)
        if match is None:
            raise invalid()
        slot, stage, event, frames = map(int, match.groups())
        if not records:
            if stage != 1 or event != 1 or frames != 0:
                raise invalid()
        if event == 1:
            if stage <= prior_stage or stage == 11:
                raise invalid()
            if prior_stage and not stage_has_outcome:
                raise invalid()
            prior_stage = stage
            stage_has_outcome = False
        elif event in (2, 3):
            if stage != prior_stage or stage_has_outcome:
                raise invalid()
            stage_has_outcome = True
        elif event == 4:
            if stage != 11 or not stage_has_outcome or exited:
                raise invalid()
            exited = True
        else:
            raise invalid()
        records.append((slot, stage, event, frames))
    return records


def read_strict(path: Path) -> tuple[dict[str, Any], list[tuple[int, int, int, int]]]:
    """Read via stage-168's bounded two-pass file check, then strict FSM."""
    base = read_journal(path)
    # The underlying stable file read is the only source of raw bytes;
    # perform a second local bounded read for protocol details. For a
    # concurrent hostile mutator, this is NOT an atomic filesystem snapshot.
    try:
        data = path.read_bytes()
    except OSError:
        raise invalid() from None
    events = _events(data)
    if not events or events[0][0] != base["slot"] or len(events) != base["records"]:
        raise invalid()
    if events[-1][3] != base["last_reported_present_calls"]:
        raise invalid()
    return base, events


def compare_attempts(
    earlier: tuple[dict[str, Any], list[tuple[int, int, int, int]]],
    later: tuple[dict[str, Any], list[tuple[int, int, int, int]]],
) -> dict[str, Any]:
    first, first_events = earlier
    second, second_events = later
    if (first["slot"] >= second["slot"] or
            first["slot"] < 0 or second["slot"] > 15):
        raise ValueError("Expected two distinct chronological boot slots")
    # A second journal can follow one or more intervening attempts.
    # Slot indexes are ordered only within an unchanged 16-slot file set.
    first_failures = [step for _, step, event, _ in first_events if event == 3]
    next_failures = [step for _, step, event, _ in second_events if event == 3]
    progressed = max(step for _, step, _, _ in second_events if step <= 10)
    first_max = max(step for _, step, _, _ in first_events if step <= 10)

    if not first_failures:
        comparison = "no_first_attempt_failure_recorded"
    elif not second["ended_with_exit_marker"]:
        comparison = "followup_log_incomplete"
    elif next_failures:
        comparison = "followup_failure_recorded"
    elif (second["last_reported_present_calls"] > 0 and
          any(step == 10 and event == 2
              for _, step, event, _ in second_events)):
        comparison = "later_attempt_reached_clean_cpu_exit"
    elif progressed > first_max:
        comparison = "later_attempt_progressed_but_not_presenting"
    else:
        comparison = "no_confirmed_cpu_progress"
    return {
        "schema": SCHEMA,
        "evidence_level": "two operator-supplied CPU checkpoint logs only",
        "hardware_gpu_presentation_verified": False,
        "original_foj_assets_verified": False,
        "switch_gameplay_verified": False,
        "older_slot": first["slot"],
        "newer_slot": second["slot"],
        "intervening_slot_count": second["slot"] - first["slot"] - 1,
        "first_reported_failure_stages": [STAGES[x] for x in first_failures],
        "followup_reported_failure_stages": [STAGES[x] for x in next_failures],
        "first_maximum_entered_stage": STAGES[first_max],
        "followup_maximum_entered_stage": STAGES[progressed],
        "first_cpu_present_calls": first["last_reported_present_calls"],
        "followup_cpu_present_calls": second["last_reported_present_calls"],
        "first_exit_marker": first["ended_with_exit_marker"],
        "followup_exit_marker": second["ended_with_exit_marker"],
        "comparison": comparison,
        "interpretation": (
            "A later CPU-stage checkpoint or completed present call is not "
            "independent evidence of Nintendo Switch GPU scanout or gameplay"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True,
                        help="First private foj-boot-XX.txt copied off SD")
    parser.add_argument("--after", type=Path, required=True,
                        help="Later private foj-boot-YY.txt copied off SD")
    args = parser.parse_args()
    try:
        older = read_strict(args.before)
        newer = read_strict(args.after)
        result = compare_attempts(older, newer)
    except ValueError as exc:
        # No user names, system paths or log byte excerpts in errors.
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
