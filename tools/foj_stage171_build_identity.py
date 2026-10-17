#!/usr/bin/env python3
"""Bind research-only Switch GPU build artifacts to private manual notes.

Only fixed generated NRO/DKSH archive entries are measured. Nothing in
this program verifies running a Nintendo Switch, authenticates an operator,
proves GPU scanout, or extracts original FoJ commercial game data.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
import zipfile

from tools.foj_stage165_sd_bundle import ZIP_PREFIX
from tools.foj_stage166_hardware_observations import (
    MAX_BUNDLE_BYTES, audit as audit_operator, inspect_bundle, read_ledger,
)
from tools.foj_stage170_cpu_visual_alignment import align, read_link
from tools.foj_stage169_two_attempt_recovery import read_strict
from tools.validate_nro import validate_nro

SCHEMA = "foj-stage171-generated-build-receipt-v1"
OUTPUT_SCHEMA = "foj-stage171-research-build-cpu-visual-binding-v1"
NRO = ZIP_PREFIX + "foj-deko3d-triangle-research.nro"
MEMBERS = (
    ZIP_PREFIX + "foj-deko3d-clear-smoke.nro",
    NRO,
    ZIP_PREFIX + "gpu/foj_actor.vert.dksh",
    ZIP_PREFIX + "gpu/foj_triangle.frag.dksh",
)
SHA = re.compile(r"^[a-f0-9]{64}$")
GIT = re.compile(r"^[a-f0-9]{40}$")
MAX_RECEIPT = 4096
MAX_NRO = 16 * 1024 * 1024


def _bad() -> ValueError:
    return ValueError("Invalid or mismatched generated-only GPU build identity")


def _pairs(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise _bad()
        record[key] = value
    return record


def _fixed_bundle_digest(bundle: Path) -> tuple[str, dict[str, str]]:
    """Verify all fixed members against one stable, bounded ZIP snapshot.

    Stage 166 validates the entire ZIP and manifest. A second
    descriptor-bound, byte-identical double read must match that exact
    first digest before any per-NRO/DKSH hash may be reported.
    """
    digest = inspect_bundle(bundle)
    try:
        initial = bundle.lstat()
        if not stat.S_ISREG(initial.st_mode) or not 1 <= initial.st_size <= MAX_BUNDLE_BYTES:
            raise _bad()
        fd = os.open(bundle, os.O_RDONLY |
                     getattr(os, "O_NOFOLLOW", 0) |
                     getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            first = stream.read(MAX_BUNDLE_BYTES + 1)
            stream.seek(0)
            second = stream.read(MAX_BUNDLE_BYTES + 1)
            final = os.fstat(stream.fileno())
        named = bundle.lstat()
        def identity(m):
            return (m.st_dev, m.st_ino, m.st_mode, m.st_size,
                    m.st_mtime_ns, m.st_ctime_ns)
        if (identity(initial) != identity(opened) or
                identity(opened) != identity(final) or
                identity(final) != identity(named) or
                len(first) != initial.st_size or first != second or
                hashlib.sha256(first).hexdigest() != digest):
            raise _bad()
        with zipfile.ZipFile(BytesIO(first)) as archive:
            binaries = {
                name: hashlib.sha256(archive.read(name)).hexdigest()
                for name in MEMBERS
            }
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        raise _bad() from None
    return digest, binaries

def _validate_git_run(commit: Any, run: Any) -> None:
    if (not isinstance(commit, str) or GIT.fullmatch(commit) is None or
            type(run) is not int or not 1 <= run < 10**15):
        raise _bad()


def build_receipt(bundle: Path, commit: str, run: int) -> dict[str, Any]:
    _validate_git_run(commit, run)
    digest, hashes = _fixed_bundle_digest(bundle)
    return {
        "schema": SCHEMA,
        "provenance": "generated-only-research-ci-artifacts",
        "git_commit": commit,
        "github_run_id": run,
        "bundle_sha256": digest,
        "built_members": [
            {"sd_relative_path": name, "sha256": hashes[name]}
            for name in MEMBERS
        ],
        "switch_hardware_verified": False,
        "original_foj_assets_included": False,
    }


def write_receipt(bundle: Path, path: Path, commit: str, run: int) -> None:
    report = build_receipt(bundle, commit, run)
    try:
        with path.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2, sort_keys=True)
            output.write("\n")
    except FileExistsError:
        raise ValueError("Research receipt must be a NEW file") from None
    except OSError:
        raise _bad() from None


def read_receipt(path: Path) -> dict[str, Any]:
    try:
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode) or not 2 <= meta.st_size <= MAX_RECEIPT:
            raise _bad()
        with path.open("rb") as stream:
            raw = stream.read(MAX_RECEIPT + 1)
        if len(raw) != meta.st_size:
            raise _bad()
        result = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(_bad()),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        raise _bad() from None
    validate_receipt(result)
    return result


def validate_receipt(result: Any) -> None:
    if not isinstance(result, dict) or set(result) != {
        "schema", "provenance", "git_commit", "github_run_id",
        "bundle_sha256", "built_members", "switch_hardware_verified",
        "original_foj_assets_included",
    }:
        raise _bad()
    if (result["schema"] != SCHEMA or
            result["provenance"] != "generated-only-research-ci-artifacts" or
            result["switch_hardware_verified"] is not False or
            result["original_foj_assets_included"] is not False):
        raise _bad()
    _validate_git_run(result["git_commit"], result["github_run_id"])
    if (not isinstance(result["bundle_sha256"], str) or
            SHA.fullmatch(result["bundle_sha256"]) is None):
        raise _bad()
    rows = result["built_members"]
    if not isinstance(rows, list) or len(rows) != len(MEMBERS):
        raise _bad()
    for name, row in zip(MEMBERS, rows):
        if (not isinstance(row, dict) or set(row) != {
                "sd_relative_path", "sha256"} or
                row["sd_relative_path"] != name or
                not isinstance(row["sha256"], str) or
                SHA.fullmatch(row["sha256"]) is None):
            raise _bad()


def read_local_nro(path: Path) -> bytes:
    """Compare an explicitly supplied local SD copy, never scan directories.

    Checks the opened inode before/after two byte passes and rejects final
    symlinks / FIFOs. Does not defeat adversarial ancestor-directory swaps
    or prove the same file was launched by Switch homebrew.
    """
    if path.name != "foj-deko3d-triangle-research.nro":
        raise _bad()
    try:
        initial = path.lstat()
        if not stat.S_ISREG(initial.st_mode) or not 1 <= initial.st_size <= MAX_NRO:
            raise _bad()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            first = stream.read(MAX_NRO + 1)
            stream.seek(0)
            second = stream.read(MAX_NRO + 1)
            final = os.fstat(stream.fileno())
        named = path.lstat()
        def identity(m):
            return (m.st_dev, m.st_ino, m.st_mode, m.st_size,
                    m.st_mtime_ns, m.st_ctime_ns)
        if (identity(initial) != identity(opened) or
                identity(opened) != identity(final) or
                identity(final) != identity(named) or
                first != second or len(first) != initial.st_size):
            raise _bad()
    except OSError:
        raise _bad() from None
    try:
        validate_nro(first)
    except ValueError:
        raise _bad() from None
    return first


def verify_receipt(bundle: Path, receipt: dict[str, Any]) -> dict[str, str]:
    """Independently recheck the real CI ZIP against all receipt hashes."""
    validate_receipt(receipt)
    digest, binaries = _fixed_bundle_digest(bundle)
    if (receipt["bundle_sha256"] != digest or
            any(row["sha256"] != binaries[name]
                for name, row in zip(MEMBERS, receipt["built_members"]))):
        raise _bad()
    return binaries


def bind(
    bundle: Path, receipt: dict[str, Any], ledger: dict[str, Any],
    before: tuple, after: tuple, visual_link: dict[str, Any],
    sd_nro: Path | None = None,
) -> dict[str, Any]:
    binary_hashes = verify_receipt(bundle, receipt)
    actual_bundle = receipt["bundle_sha256"]
    # Strict structural validation and independent CPU/visual comparison.
    visual_result = align(before, after, ledger, visual_link)
    audit_operator(ledger)
    values = ledger["build"]
    asserted = {
        "git_commit": receipt["git_commit"],
        "github_run_id": receipt["github_run_id"],
        "sd_bundle_sha256": actual_bundle,
    }
    filled = 0
    for name, expected in asserted.items():
        supplied = values[name]
        if supplied is not None:
            if type(supplied) is not type(expected) or supplied != expected:
                raise _bad()
            filled += 1
    metadata_status = (
        "operator_recorded_build_identity_matches_receipt"
        if filled == 3 else
        "operator_build_metadata_missing"
        if filled == 0 else
        "operator_build_metadata_incomplete"
    )
    copy_checked = sd_nro is not None
    if copy_checked and hashlib.sha256(read_local_nro(sd_nro)).hexdigest() != binary_hashes[NRO]:
        raise _bad()
    return {
        "schema": OUTPUT_SCHEMA,
        "evidence_level": "generated-bundle-integrity-and-operator-claims-only",
        "artifact_bundle_verified": True,
        "receipt_matches_research_archive": True,
        "operator_build_metadata_status": metadata_status,
        "operator_declared_build_fields": filled,
        "sd_nro_copy_compared": copy_checked,
        "sd_nro_copy_matches_generated_archive": copy_checked,
        "cpu_recovery_comparison": visual_result["cpu_recovery_comparison"],
        "cpu_visual_alignment": visual_result["cpu_visual_alignment"],
        "operator_scenario_link_explicit": visual_result["operator_link_explicit"],
        "overall_interpretation": (
            "operator_build_and_visual_claims_consistent_but_unverified"
            if filled == 3 and visual_result["operator_link_explicit"] and
            visual_result["cpu_visual_alignment"] ==
                "cpu_and_operator_declarations_consistent_unverified"
            else "incomplete_or_unconfirmed_manual_test_evidence"
        ),
        "hardware_execution_verified": False,
        "gpu_scanout_verified": False,
        "original_foj_assets_verified": False,
        "switch_gameplay_verified": False,
        "limits": (
            "Matching SHA-256 proves equality of these locally supplied "
            "generated build bytes only, not that a console executed them "
            "or that any claimed screen was actually observed"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--create-receipt", type=Path,
                        help="Exclusive-new generated-only artifact identity JSON")
    parser.add_argument("--verify-receipt", type=Path,
                        help="Validate CI archive/receipt without private operator files")
    parser.add_argument("--git-commit", type=str)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--link", type=Path)
    parser.add_argument("--sd-nro", type=Path,
                        help="Optional local copy; NEVER proof this NRO was launched")
    args = parser.parse_args()
    try:
        if args.create_receipt is not None:
            if (args.verify_receipt is not None or
                    args.git_commit is None or args.run_id is None or
                    any(x is not None for x in
                        (args.receipt, args.ledger, args.before,
                         args.after, args.link, args.sd_nro))):
                raise _bad()
            write_receipt(args.bundle, args.create_receipt,
                          args.git_commit, args.run_id)
            print("Generated-only research identity receipt created; NO Switch tested")
        elif args.verify_receipt is not None:
            if any(x is not None for x in
                    (args.git_commit, args.run_id, args.receipt, args.ledger,
                     args.before, args.after, args.link, args.sd_nro)):
                raise _bad()
            verify_receipt(args.bundle, read_receipt(args.verify_receipt))
            print("Generated-only ZIP and four NRO/DKSH hashes match CI receipt; "
                  "no console hardware verified")
        else:
            if (args.git_commit is not None or args.run_id is not None or
                    any(x is None for x in
                        (args.receipt, args.ledger, args.before, args.after, args.link))):
                raise _bad()
            result = bind(
                args.bundle, read_receipt(args.receipt),
                read_ledger(args.ledger),
                read_strict(args.before), read_strict(args.after),
                read_link(args.link), args.sd_nro,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        parser.error("Invalid or mismatched generated-only GPU build identity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
