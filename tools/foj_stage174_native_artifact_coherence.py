#!/usr/bin/env python3
"""Stage 174: compare loose native research NRO/DKSH with the fixed SD ZIP.

Checks local generated-only build file identity, NOT physical Nintendo
Switch execution, GPU presentation, or original game asset provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.foj_fd_bound_reader import open_regular_beneath
from tools.foj_stage165_sd_bundle import INPUTS, MAX_NRO_BYTES, ZIP_PREFIX
from tools.foj_stage171_build_identity import (
    MEMBERS, read_receipt, verify_receipt,
)
from tools.validate_dksh import inspect_dksh
from tools.validate_nro import validate_nro

SCHEMA = "foj-stage174-loose-native-artifact-coherence-v1"
MAX_DKSH_BYTES = 8 * 1024 * 1024


def _bad() -> ValueError:
    return ValueError("Invalid or mismatched generated-only native artifact coherence")


def _stable_loose_bytes(root: Path, relative: str, kind: str) -> bytes:
    """Use anchored directories and a stable regular-file descriptor.

    Fixed repository-relative paths only; never inspect arbitrary PS3 data,
    enumerate folders, or print the caller's local absolute paths.
    """
    if kind not in ("nro", "vertex", "fragment"):
        raise _bad()
    limit = MAX_NRO_BYTES if kind == "nro" else MAX_DKSH_BYTES
    try:
        with open_regular_beneath(root, relative) as (stream, metadata):
            if not 1 <= metadata.st_size <= limit:
                raise _bad()
            first = stream.read(limit + 1)
            stream.seek(0)
            second = stream.read(limit + 1)
            if len(first) != metadata.st_size or first != second:
                raise _bad()
        if kind == "nro":
            validate_nro(first)
        else:
            inspect_dksh(first, expected_stage=kind)
    except (OSError, ValueError, TypeError):
        raise _bad() from None
    return first


def verify_native_outputs(
    root: Path, bundle: Path, receipt: dict[str, Any],
    expected_commit: str, expected_run_id: int,
) -> dict[str, Any]:
    """Verify ZIP receipt, declared CI identity, and four loose SDK files.

    Output is a local consistency report, not a hardware attestation.
    """
    if (not isinstance(root, Path) or
            type(expected_commit) is not str or
            type(expected_run_id) is not int):
        raise _bad()
    if (receipt.get("git_commit") != expected_commit or
            receipt.get("github_run_id") != expected_run_id):
        raise _bad()

    # Fail closed if the expected fixed build-to-ZIP path mapping drifts.
    if tuple(ZIP_PREFIX + staged for _, staged, _ in INPUTS) != MEMBERS:
        raise _bad()
    expected_hashes = verify_receipt(bundle, receipt)
    rows = []
    for relative, staged, kind in INPUTS:
        member = ZIP_PREFIX + staged
        data = _stable_loose_bytes(root, relative, kind)
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_hashes[member]:
            raise _bad()
        rows.append({
            "sd_relative_path": member,
            "sha256": digest,
            "matches_zip_receipt": True,
        })
    return {
        "schema": SCHEMA,
        "provenance": "generated-only-native-research-build",
        "git_commit_declared": expected_commit,
        "github_run_id_declared": expected_run_id,
        "bundle_sha256": receipt["bundle_sha256"],
        "binary_count": len(rows),
        "matching_binaries": rows,
        "loose_and_zip_consistent_at_check_time": True,
        "switch_hardware_execution_verified": False,
        "gpu_scanout_verified": False,
        "original_foj_assets_verified": False,
        "gameplay_verified": False,
    }


def write_gate(path: Path, report: dict[str, Any]) -> None:
    """Publish only to an exclusively new path after successful validation."""
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
    except (OSError, FileExistsError):
        raise _bad() from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-run-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="Exclusive-new generated research consistency report")
    args = parser.parse_args()
    try:
        report = verify_native_outputs(
            args.repo_root, args.bundle, read_receipt(args.receipt),
            args.expected_commit, args.expected_run_id,
        )
        write_gate(args.output, report)
    except (ValueError, OSError, TypeError, KeyError, RecursionError):
        parser.error("Invalid or mismatched generated-only native artifact coherence")
    print("Four generated loose NRO/DKSH files match the declared CI ZIP receipt;"
          " no Switch hardware execution verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
