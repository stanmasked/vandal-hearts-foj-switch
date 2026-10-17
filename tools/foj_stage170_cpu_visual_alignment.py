#!/usr/bin/env python3
"""Compare declared Switch GPU visuals against two private CPU boot logs.

This reads local operator statements only. Nothing here sees a Switch,
attests a screenshot, proves GPU scanout, or imports PS3 game assets.
A visual scenario is NEVER automatically associated with a boot run:
the operator must fill a separate explicit, local-only linkage form.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.foj_stage166_hardware_observations import (
    SCENARIOS, audit, read_ledger,
)
from tools.foj_stage173_private_json_snapshot import read_private_json_bytes
from tools.foj_stage169_two_attempt_recovery import (
    compare_attempts, read_strict,
)

SCHEMA = "foj-stage170-operator-scenario-link-v1"
OUTPUT_SCHEMA = "foj-stage170-cpu-visual-alignment-v1"
LINK_BASIS = "operator_reports_same_launch"
MAX_BYTES = 2048


def _invalid() -> ValueError:
    return ValueError("Invalid or unverified local CPU/visual linkage")


def blank_link() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "boot_slot": None,
        "visual_scenario": None,
        "association_basis": None,
    }


def create_blank_link(path: Path) -> None:
    # Existing private files must never be overwritten.
    try:
        with path.open("x", encoding="utf-8") as output:
            json.dump(blank_link(), output, indent=2, sort_keys=True)
            output.write("\n")
    except FileExistsError:
        raise ValueError("Link form must be a new file") from None
    except OSError:
        raise _invalid() from None


def _no_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _invalid()
        result[key] = value
    return result


def read_link(path: Path) -> dict[str, Any]:
    try:
        data = read_private_json_bytes(path, MAX_BYTES)
        result = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_no_duplicate_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(_invalid()),
        )
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        raise _invalid() from None
    validate_link(result)
    return result


def validate_link(form: Any) -> None:
    if (not isinstance(form, dict) or
            set(form) != {"schema", "boot_slot", "visual_scenario",
                         "association_basis"} or
            form["schema"] != SCHEMA):
        raise _invalid()
    blank = all(form[key] is None for key in (
        "boot_slot", "visual_scenario", "association_basis"))
    if blank:
        return
    if (type(form["boot_slot"]) is not int or
            not 0 <= form["boot_slot"] <= 15 or
            type(form["visual_scenario"]) is not str or
            form["visual_scenario"] not in SCENARIOS or
            form["association_basis"] != LINK_BASIS):
        raise _invalid()


def align(
    older: tuple,
    newer: tuple,
    observations: dict[str, Any],
    link: dict[str, Any],
) -> dict[str, Any]:
    """Validate all three inputs, retain operator-only evidence labels."""
    validate_link(link)
    recovery = compare_attempts(older, newer)
    operator = audit(observations)  # Full stage-166 schema validation.
    result = {
        "schema": OUTPUT_SCHEMA,
        "evidence_level": "operator-declared association; no independent GPU evidence",
        "hardware_execution_verified": False,
        "gpu_scanout_verified": False,
        "original_foj_assets_verified": False,
        "switch_gameplay_verified": False,
        "cpu_recovery_comparison": recovery["comparison"],
        "older_slot": recovery["older_slot"],
        "newer_slot": recovery["newer_slot"],
        "linked_slot": None,
        "linked_scenario": None,
        "linked_observed_stages": 0,
        "operator_visual_expected_comparison": "not_linked",
        "cpu_visual_alignment": "not_linked",
        "operator_link_explicit": False,
        "limitations": (
            "Both logs and visible outcomes are supplied by an operator; "
            "this tool cannot authenticate their shared run identity "
            "or confirm any frame on a physical Nintendo Switch"
        ),
    }
    if link["boot_slot"] is None:
        return result
    slot = link["boot_slot"]
    if slot not in (recovery["older_slot"], recovery["newer_slot"]):
        raise _invalid()
    scenario = link["visual_scenario"]
    expected = SCENARIOS[scenario]
    row = next(item for item in observations["scenarios"] if item["id"] == scenario)
    seen = tuple(item["seen"] for item in row["observations"])
    populated = sum(value is not None for value in seen)
    expected_label = (
        "not_observed" if populated == 0 else
        "incomplete" if populated < 3 else
        "matches_synthetic_expectations" if seen == expected else
        "differs_from_synthetic_expectations"
    )
    boot = older if slot == recovery["older_slot"] else newer
    boot_summary, events = boot
    # Strictly compare actual recorded ENTER/READY stages, without
    # assuming that a counted CPU present call means visible scanout.
    ready_present = any(
        stage == 10 and event == 2 and frames > 0
        for _, stage, event, frames in events
    )
    failed_early = any(
        event == 3 and stage <= 6 for _, stage, event, _ in events
    )
    if populated == 0:
        alignment = "no_operator_visual_observation"
    elif populated < 3:
        alignment = "incomplete_operator_visual_observation"
    elif expected_label == "differs_from_synthetic_expectations":
        alignment = "operator_visual_differs_from_test_expectations"
    elif failed_early or not ready_present:
        alignment = "cpu_journal_does_not_support_visual_sequence"
    else:
        alignment = "cpu_and_operator_declarations_consistent_unverified"
    result.update({
        "linked_slot": slot,
        "linked_scenario": scenario,
        "linked_observed_stages": populated,
        "operator_visual_expected_comparison": expected_label,
        "cpu_visual_alignment": alignment,
        "operator_link_explicit": True,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--init-link", type=Path,
                        help="Create NEW blank binding template locally")
    parser.add_argument("--before", type=Path, help="Older private boot log")
    parser.add_argument("--after", type=Path, help="Later private boot log")
    parser.add_argument("--ledger", type=Path,
                        help="Private stage-166 visual observation worksheet")
    parser.add_argument("--link", type=Path,
                        help="Manually filled explicit boot-to-scenario link")
    args = parser.parse_args()
    try:
        if args.init_link is not None:
            if any(x is not None for x in (
                    args.before, args.after, args.ledger, args.link)):
                raise _invalid()
            create_blank_link(args.init_link)
            print("Created BLANK operator-only scenario link; no Switch observed")
            return 0
        if any(x is None for x in (
                args.before, args.after, args.ledger, args.link)):
            raise _invalid()
        report = align(
            read_strict(args.before),
            read_strict(args.after),
            read_ledger(args.ledger),
            read_link(args.link),
        )
    except (ValueError, KeyError, TypeError):
        # Do not echo filenames, content, game bytes or operator metadata.
        parser.error("Invalid or inconsistent private GPU observation input")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
