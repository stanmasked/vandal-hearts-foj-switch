#!/usr/bin/env python3
"""Private, offline Switch GPU smoke-test observation ledger.

Does not connect to Nintendo Switch, capture frames, attest an operator,
view photographs, or independently verify claimed hardware observations.
Blank fields must stay blank until someone actually witnesses the screen.
Any report is explicitly *operator-reported*, never automated GPU evidence.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile
from typing import Any

from tools.foj_stage173_private_json_snapshot import read_private_json_bytes
from tools.foj_stage162_synthetic_dds import generated_dds
from tools.foj_stage165_sd_bundle import INPUTS, ZIP_PREFIX
from tools.validate_dksh import inspect_dksh
from tools.validate_nro import validate_nro

SCHEMA = "foj-stage166-operator-gpu-observations-v1"
STAGES = ("slot0", "slot1", "after_240")
SCENARIOS = {
    "A": ("blue", "blue", "two_fallback_quads"),
    "B": ("green", "blue", "checkerboard_plus_fallback"),
    "C": ("green", "green", "two_checkerboards"),
    "D": ("green", "amber", "error_held"),
    "E": ("green", "green", "two_checkerboards"),
}
VISUALS = frozenset((
    "green", "blue", "amber", "magenta", "red", "orange",
    "dark_red", "two_fallback_quads", "checkerboard_plus_fallback",
    "two_checkerboards", "error_held", "black_screen",
    "unexpected_output",
))
SHA = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
MAX_REPORT_BYTES = 64 * 1024
MAX_BUNDLE_BYTES = 40 * 1024 * 1024
BUNDLE_FILES = {
    ZIP_PREFIX + staged: kind for _, staged, kind in INPUTS
}
BUNDLE_FILES.update({
    ZIP_PREFIX + "gpu/material0.dds": "dds0",
    ZIP_PREFIX + "gpu/material1.dds": "dds1",
    "README_STAGE165.txt": "readme",
    "MANIFEST_STAGE165.json": "manifest",
})


def _bad() -> ValueError:
    return ValueError("Invalid private hardware observation ledger")


def _exact_keys(obj: Any, keys: set[str]) -> None:
    if not isinstance(obj, dict) or set(obj) != keys:
        raise _bad()


def _pairs_no_duplicates(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise _bad()
        result[name] = value
    return result


def blank_template() -> dict[str, Any]:
    """All observations empty: no generated example is marked as witnessed."""
    return {
        "schema": SCHEMA,
        "build": {
            "git_commit": None,
            "github_run_id": None,
            "sd_bundle_sha256": None,
        },
        "hardware": {
            "model": None,
            "homebrew_mode": None,
            "local_test_date": None,
        },
        "startup": {
            "clear_smoke_visual": None,
            "triangle_launch_visual": None,
            "triangle_exit_observed": None,
            "failure_phase_observed": None,
        },
        "scenarios": [
            {"id": sid, "observations": [
                {"stage": stage, "seen": None, "capture_sha256": None}
                for stage in STAGES
            ]}
            for sid in SCENARIOS
        ],
    }


def write_template(path: Path, *, bundle_sha256: str | None = None) -> None:
    if bundle_sha256 is not None and not SHA.fullmatch(bundle_sha256):
        raise ValueError("Invalid local research bundle digest")
    document = blank_template()
    if bundle_sha256 is not None:
        # Only the verified archive digest is pre-populated. No screen,
        # initialization, device, or operator observation is invented.
        document["build"]["sd_bundle_sha256"] = bundle_sha256
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    except FileExistsError:
        raise ValueError("Observation template must be a NEW file") from None
    except OSError:
        raise ValueError("Unable to create local observation template") from None


def read_ledger(path: Path) -> dict[str, Any]:
    try:
        raw = read_private_json_bytes(path, MAX_REPORT_BYTES)
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=lambda _: (_ for _ in ()).throw(_bad()),
        )
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        raise _bad() from None


def _optional_hash(value: Any, pattern=SHA) -> bool:
    return value is None or (isinstance(value, str) and pattern.fullmatch(value) is not None)


def _check_build_hardware(ledger: dict[str, Any]) -> bool:
    build = ledger["build"]
    hardware = ledger["hardware"]
    _exact_keys(build, {"git_commit", "github_run_id", "sd_bundle_sha256"})
    _exact_keys(hardware, {"model", "homebrew_mode", "local_test_date"})
    if not _optional_hash(build["git_commit"], COMMIT):
        raise _bad()
    if not _optional_hash(build["sd_bundle_sha256"]):
        raise _bad()
    run = build["github_run_id"]
    if run is not None and (type(run) is not int or not 1 <= run < 10**15):
        raise _bad()
    model = hardware["model"]
    mode = hardware["homebrew_mode"]
    day = hardware["local_test_date"]
    if model is not None and model not in ("original", "lite", "oled", "unknown"):
        raise _bad()
    if mode is not None and mode not in (
            "homebrew_menu_applet", "homebrew_menu_title", "other", "unknown"):
        raise _bad()
    if day is not None:
        if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            raise _bad()
        try:
            dt.date.fromisoformat(day)
        except ValueError:
            raise _bad() from None
    return all(value is not None for value in list(build.values()) +
               list(hardware.values()))


def audit(ledger: dict[str, Any], *, bundle_sha256: str | None = None) -> dict[str, Any]:
    """Compare declarations against expected screens; NEVER attest to hardware."""
    _exact_keys(ledger, {"schema", "build", "hardware", "startup", "scenarios"})
    if ledger["schema"] != SCHEMA:
        raise _bad()
    metadata_complete = _check_build_hardware(ledger)
    startup = ledger["startup"]
    _exact_keys(startup, {
        "clear_smoke_visual", "triangle_launch_visual",
        "triangle_exit_observed", "failure_phase_observed"})
    choices = {
        "clear_smoke_visual": {"alternating_colors", "black_screen", "unexpected_output"},
        "triangle_launch_visual": {"dds_status_screen", "black_screen", "unexpected_output"},
        "triangle_exit_observed": {
            "plus_clean", "plus_nonzero_reported", "freeze_or_crash",
            "not_visible_in_homebrew"},
        "failure_phase_observed": {
            "before_first_frame", "during_dds_status",
            "during_textured_scene", "no_failure_observed", "unknown"},
    }
    for name, value in startup.items():
        if value is not None and (
                type(value) is not str or value not in choices[name]):
            raise _bad()
    # Startup statuses are descriptions of visible effects, not assertions
    # about the device driver, libnx error source, or SDK correctness.
    startup_count = sum(v is not None for v in startup.values())
    scenarios = ledger["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != len(SCENARIOS):
        raise _bad()
    if bundle_sha256 is not None:
        if not SHA.fullmatch(bundle_sha256) or (
                ledger["build"]["sd_bundle_sha256"] != bundle_sha256):
            raise ValueError("Local research ZIP digest does not match operator ledger")
    results = []
    total_observed = 0
    capture_count = 0
    for item, (sid, expected) in zip(scenarios, SCENARIOS.items()):
        _exact_keys(item, {"id", "observations"})
        if item["id"] != sid:
            raise _bad()
        observations = item["observations"]
        if not isinstance(observations, list) or len(observations) != 3:
            raise _bad()
        observed = []
        for stage, record in zip(STAGES, observations):
            _exact_keys(record, {"stage", "seen", "capture_sha256"})
            if record["stage"] != stage or not _optional_hash(record["capture_sha256"]):
                raise _bad()
            seen = record["seen"]
            if seen is not None and (type(seen) is not str or seen not in VISUALS):
                raise _bad()
            # A capture hash with no observation would imply fake binding.
            if seen is None and record["capture_sha256"] is not None:
                raise _bad()
            if seen is not None:
                total_observed += 1
                if record["capture_sha256"] is not None:
                    capture_count += 1
            observed.append(seen)
        filled = sum(x is not None for x in observed)
        result = ("not_observed" if filled == 0 else
                  "incomplete" if filled < 3 else
                  "matches_expected" if tuple(observed) == expected else
                  "differs_from_expected")
        results.append({"scenario": sid, "declared_stages": filled,
                        "comparison": result})
    return {
        "schema": "foj-stage166-operator-audit-v1",
        "evidence_level": "operator-declared-only; no automatic hardware attestation",
        "hardware_execution_verified": False,
        "original_foj_assets_verified": False,
        "environment_metadata_complete": metadata_complete,
        "locally_supplied_bundle_hash_matched": bundle_sha256 is not None,
        "declared_startup_fields": startup_count,
        "declared_screen_stages": total_observed,
        "declared_capture_hashes": capture_count,
        "scenarios": results,
        "interpretation": (
            "Expected-color comparisons are against user-entered statements, "
            "not computer vision, GPU telemetry, or physical Switch observations"
        ),
    }


def inspect_bundle(path: Path) -> str:
    """Verify fixed synthetic SD ZIP contents locally without extracting it."""
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or not 1 <= metadata.st_size <= MAX_BUNDLE_BYTES:
            raise _bad()
        with path.open("rb") as stream:
            raw = stream.read(MAX_BUNDLE_BYTES + 1)
        if len(raw) != metadata.st_size:
            raise _bad()
        from io import BytesIO
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            infos = archive.infolist()
            if (len(infos) != len(BUNDLE_FILES) or
                    {i.filename for i in infos} != set(BUNDLE_FILES) or
                    any(i.compress_type != zipfile.ZIP_STORED or
                        i.file_size > 16 * 1024 * 1024 or
                        i.filename.startswith("/") or ".." in Path(i.filename).parts
                        for i in infos)):
                raise _bad()
            blobs = {i.filename: archive.read(i) for i in infos}
        manifest = json.loads(blobs["MANIFEST_STAGE165.json"].decode("utf-8"),
                              object_pairs_hook=_pairs_no_duplicates)
        _exact_keys(manifest, {
            "schema", "provenance", "files", "ps3_assets_included",
            "switch_hardware_tested", "playable_game"})
        if (manifest["schema"] != "foj-stage165-generated-gpu-sd-bundle-v1" or
                manifest["ps3_assets_included"] is not False or
                manifest["switch_hardware_tested"] is not False or
                manifest["playable_game"] is not False):
            raise _bad()
        listed = manifest["files"]
        if not isinstance(listed, list) or len(listed) != len(BUNDLE_FILES)-1:
            raise _bad()
        listed_names = []
        for row in listed:
            _exact_keys(row, {"sd_relative_path", "size_bytes", "sha256"})
            name = row["sd_relative_path"]
            if name not in BUNDLE_FILES or name == "MANIFEST_STAGE165.json":
                raise _bad()
            if (type(row["size_bytes"]) is not int or
                    row["size_bytes"] != len(blobs[name]) or
                    row["sha256"] != hashlib.sha256(blobs[name]).hexdigest()):
                raise _bad()
            listed_names.append(name)
        if len(set(listed_names)) != len(BUNDLE_FILES)-1:
            raise _bad()
        for name, kind in BUNDLE_FILES.items():
            if kind == "nro":
                validate_nro(blobs[name])
            elif kind in ("vertex", "fragment"):
                inspect_dksh(blobs[name], expected_stage=kind)
            elif kind.startswith("dds"):
                if blobs[name] != generated_dds(int(kind[-1])):
                    raise _bad()
        return hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, KeyError, TypeError, IndexError, zipfile.BadZipFile,
            UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("Invalid or unsupported local research SD bundle") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init", type=Path, help="Create NEW blank local observations JSON")
    mode.add_argument("--audit", type=Path, help="Audit manually filled local JSON")
    parser.add_argument("--bundle", type=Path,
                        help="Optional local stage-165 ZIP whose SHA-256 is recorded")
    args = parser.parse_args()
    try:
        if args.init:
            digest = inspect_bundle(args.bundle) if args.bundle else None
            write_template(args.init, bundle_sha256=digest)
            print("Created BLANK, unverified local hardware observation template")
        else:
            digest = inspect_bundle(args.bundle) if args.bundle else None
            result = audit(read_ledger(args.audit), bundle_sha256=digest)
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
