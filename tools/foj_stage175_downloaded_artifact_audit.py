#!/usr/bin/env python3
"""Stage 175: audit ALL five published research NRO/DKSH after download.

This independently re-reads files downloaded from an Actions artifact.
It validates unsigned local consistency, not GitHub authenticity or
execution/scanout on physical Nintendo Switch hardware.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

from tools.foj_fd_bound_reader import open_regular_beneath
from tools.foj_stage165_sd_bundle import INPUTS
from tools.foj_stage166_hardware_observations import blank_template
from tools.foj_stage171_build_identity import read_receipt
from tools.foj_stage174_native_artifact_coherence import (
    _stable_loose_bytes, verify_native_outputs,
)

SCHEMA = "foj-stage175-five-published-native-binaries-v1"
STAGE171 = "build/foj-stage171-ci-build-receipt.json"
STAGE174 = "build/foj-stage174-loose-coherence.json"
STAGE175 = "build/foj-stage175-five-binary-receipt.json"
BUNDLE = "build/foj-stage165-gpu-sd-smoke.zip"
EXTRA = ("gpu/build/foj_actor.frag.dksh", "fragment")
OUTPUT_FILES = frozenset({
    *(relative for relative, _, _ in INPUTS), EXTRA[0],
    BUNDLE, "build/foj-stage166-blank-observations.json",
    STAGE171, STAGE174, STAGE175,
})
OUTPUT_DIRS = frozenset({"build", "gpu", "gpu/build"})
MAX_JSON = 8192


def _bad() -> ValueError:
    return ValueError("Invalid or mismatched downloaded research artifact")


def _pairs(rows: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in rows:
        if key in result:
            raise _bad()
        result[key] = value
    return result


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    try:
        with open_regular_beneath(root, relative) as (stream, metadata):
            if not 2 <= metadata.st_size <= MAX_JSON:
                raise _bad()
            first = stream.read(MAX_JSON + 1)
            stream.seek(0)
            second = stream.read(MAX_JSON + 1)
            if len(first) != metadata.st_size or first != second:
                raise _bad()
        value = json.loads(first.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(_bad()))
        if not isinstance(value, dict):
            raise _bad()
        return value
    except (OSError, ValueError, UnicodeError, RecursionError, TypeError):
        raise _bad() from None


def _check_downloaded_inventory(root: Path) -> None:
    """Reject unknown paths and symbolic links in the downloaded payload.

    The artifact is expected to hold exactly the published research files;
    no private directory enumeration or external paths are included in reports.
    """
    # Anchor every directory descent at its already-open parent.
    # os.scandir(path) alone could follow an ancestor replaced by a
    # symlink after the earlier inventory pass.
    flags = (os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) |
             getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    if not getattr(os, "O_NOFOLLOW", 0) or not getattr(os, "O_DIRECTORY", 0):
        raise _bad()
    seen_files: set[str] = set()
    seen_dirs: set[str] = set()
    count = 0

    def descend(fd: int, prefix: str) -> None:
        nonlocal count
        with os.scandir(fd) as entries:
            for entry in entries:
                count += 1
                if count > 24 or entry.name in (".", "..") or "/" in entry.name:
                    raise _bad()
                relative = prefix + entry.name
                meta = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(meta.st_mode):
                    if relative not in OUTPUT_DIRS or relative in seen_dirs:
                        raise _bad()
                    seen_dirs.add(relative)
                    child = os.open(entry.name, flags, dir_fd=fd)
                    try:
                        opened = os.fstat(child)
                        if (not stat.S_ISDIR(opened.st_mode) or
                                (opened.st_dev, opened.st_ino) !=
                                (meta.st_dev, meta.st_ino)):
                            raise _bad()
                        descend(child, relative + "/")
                    finally:
                        os.close(child)
                elif stat.S_ISREG(meta.st_mode):
                    if relative not in OUTPUT_FILES or relative in seen_files:
                        raise _bad()
                    seen_files.add(relative)
                else:
                    raise _bad()

    try:
        root_fd = os.open(root, flags)
        try:
            descend(root_fd, "")
        finally:
            os.close(root_fd)
    except (OSError, ValueError):
        raise _bad() from None
    if seen_files != OUTPUT_FILES or seen_dirs != OUTPUT_DIRS:
        raise _bad()


def build_five_receipt(root: Path, expected_commit: str, expected_run_id: int) -> dict[str, Any]:
    """Verify existing ZIP + stage-174 results, then hash fifth loose DKSH."""
    try:
        receipt = read_receipt(root / STAGE171)
        previous = verify_native_outputs(
            root, root / BUNDLE, receipt, expected_commit, expected_run_id,
        )
        if _read_json(root, STAGE174) != previous:
            raise _bad()
        if _read_json(root, "build/foj-stage166-blank-observations.json") != blank_template():
            raise _bad()
        rows = [
            {"published_relative_path": relative, "sha256": entry["sha256"]}
            for (relative, _, _), entry in zip(
                INPUTS, previous["matching_binaries"], strict=True
            )
        ]
        extra_data = _stable_loose_bytes(root, *EXTRA)
        rows.append({
            "published_relative_path": EXTRA[0],
            "sha256": hashlib.sha256(extra_data).hexdigest(),
        })
        return {
            "schema": SCHEMA,
            "provenance": "generated-only-published-research-binaries",
            "git_commit_declared": expected_commit,
            "github_run_id_declared": expected_run_id,
            "bundle_sha256": receipt["bundle_sha256"],
            "published_binaries": rows,
            "published_binary_count": 5,
            "stage174_zip_consistency_rechecked": True,
            "physical_switch_execution_verified": False,
            "gpu_scanout_verified": False,
            "original_foj_assets_verified": False,
            "gameplay_verified": False,
        }
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        raise _bad() from None


def create_receipt(root: Path, expected_commit: str, expected_run_id: int) -> None:
    manifest = build_five_receipt(root, expected_commit, expected_run_id)
    try:
        with (root / STAGE175).open("x", encoding="utf-8") as output:
            json.dump(manifest, output, sort_keys=True, indent=2)
            output.write("\n")
    except OSError:
        raise _bad() from None


def verify_download(root: Path, expected_commit: str, expected_run_id: int) -> None:
    """Independently re-read the downloaded artifact rather than the build tree."""
    _check_downloaded_inventory(root)
    claimed = _read_json(root, STAGE175)
    actual = build_five_receipt(root, expected_commit, expected_run_id)
    if claimed != actual:
        raise _bad()
    # Detect ordinary file-set substitutions during the content audit.
    _check_downloaded_inventory(root)
    if _read_json(root, STAGE175) != claimed:
        raise _bad()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-run-id", type=int, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create-receipt", action="store_true")
    mode.add_argument("--verify-downloaded", action="store_true")
    args = parser.parse_args()
    try:
        if args.create_receipt:
            create_receipt(args.artifact_root, args.expected_commit,
                           args.expected_run_id)
            print("Five generated binary hashes recorded; no Switch hardware checked")
        else:
            verify_download(args.artifact_root, args.expected_commit,
                            args.expected_run_id)
            print("Downloaded artifact: five native binaries and ZIP receipts agree;"
                  " no Switch execution or GPU scanout verified")
    except (ValueError, TypeError, OSError, RecursionError):
        parser.error("Invalid or mismatched downloaded research artifact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
