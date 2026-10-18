#!/usr/bin/env python3
"""Stage 178: read-only byte comparison of a copied synthetic Switch SD tree.

Compares the six fixed files expected under switch/foj/ with a verified
generated-only research ZIP and its unsigned CI identity receipt.
Neither a matching SD copy nor this tool proves hardware execution.
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
from tools.foj_stage162_synthetic_dds import generated_dds
from tools.foj_stage165_sd_bundle import INPUTS, MAX_NRO_BYTES
from tools.foj_stage171_build_identity import read_receipt, verify_receipt
from tools.validate_dksh import inspect_dksh
from tools.validate_nro import validate_nro

SCHEMA = "foj-stage178-local-sd-copy-preflight-v1"
STAGED_FILES = tuple(
    (staged, "switch/foj/" + staged, kind)
    for _build, staged, kind in INPUTS
) + tuple(
    (f"gpu/material{n}.dds", f"switch/foj/gpu/material{n}.dds", "dds")
    for n in range(2)
)
EXPECTED_FOJ = frozenset({"foj-deko3d-clear-smoke.nro",
                          "foj-deko3d-triangle-research.nro", "gpu"})
EXPECTED_GPU = frozenset({"foj_actor.vert.dksh", "foj_triangle.frag.dksh",
                          "material0.dds", "material1.dds"})
MAX_SHADER = 8 * 1024 * 1024


def _bad() -> ValueError:
    return ValueError("Invalid or mismatched generated-only SD research copy")


def _identity(st: os.stat_result) -> tuple[int, ...]:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size,
            st.st_mtime_ns, st.st_ctime_ns)


def _snapshot_foj_tree(sd_root: Path) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Inspect only switch/foj, allowing unrelated files elsewhere on SD.

    Each directory component is opened relative to a held parent with
    O_NOFOLLOW. Reject missing/extra entries, links and special files.
    The returned file metadata is compared before and after byte reads.
    """
    directory = getattr(os, "O_DIRECTORY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not directory or not nofollow or not isinstance(sd_root, Path):
        raise _bad()
    flags = os.O_RDONLY | directory | nofollow | getattr(os, "O_CLOEXEC", 0)
    held = []
    try:
        current = os.open(sd_root, flags)
        held.append(current)
        for name in ("switch", "foj"):
            next_fd = os.open(name, flags, dir_fd=current)
            held.append(next_fd)
            current = next_fd

        records: list[tuple[str, tuple[int, ...]]] = []

        def inspect(fd: int, expected: frozenset[str], prefix: str) -> None:
            begin = os.fstat(fd)
            with os.scandir(fd) as iterator:
                names = [entry.name for entry in iterator]
            if len(names) != len(expected) or set(names) != expected:
                raise _bad()
            if len(names) != len(set(names)):
                raise _bad()
            for name in sorted(names):
                meta = os.stat(name, dir_fd=fd, follow_symlinks=False)
                identity = _identity(meta)
                rel = prefix + name
                if name == "gpu" and prefix == "":
                    if not stat.S_ISDIR(meta.st_mode):
                        raise _bad()
                    child = os.open(name, flags, dir_fd=fd)
                    held.append(child)
                    if _identity(os.fstat(child)) != identity:
                        raise _bad()
                    inspect(child, EXPECTED_GPU, "gpu/")
                    if (_identity(os.fstat(child)) != identity or
                            _identity(os.stat(name, dir_fd=fd,
                                              follow_symlinks=False)) != identity):
                        raise _bad()
                else:
                    if not stat.S_ISREG(meta.st_mode):
                        raise _bad()
                    records.append((rel, identity))
                    if _identity(os.stat(name, dir_fd=fd,
                                          follow_symlinks=False)) != identity:
                        raise _bad()
            if _identity(os.fstat(fd)) != _identity(begin):
                raise _bad()

        inspect(current, EXPECTED_FOJ, "")
        return tuple(sorted(records))
    except (OSError, ValueError, TypeError):
        raise _bad() from None
    finally:
        for descriptor in reversed(held):
            os.close(descriptor)


def _read_copied(sd_root: Path, relative: str, kind: str) -> bytes:
    ceiling = MAX_NRO_BYTES if kind == "nro" else (
        MAX_SHADER if kind in ("vertex", "fragment") else 384)
    try:
        with open_regular_beneath(sd_root, relative) as (stream, info):
            if not 1 <= info.st_size <= ceiling:
                raise _bad()
            a = stream.read(ceiling + 1)
            stream.seek(0)
            b = stream.read(ceiling + 1)
            if a != b or len(a) != info.st_size:
                raise _bad()
        if kind == "nro":
            validate_nro(a)
        elif kind in ("vertex", "fragment"):
            inspect_dksh(a, expected_stage=kind)
    except (OSError, ValueError, TypeError):
        raise _bad() from None
    return a


def audit_sd_copy(sd_root: Path, bundle: Path, receipt: dict[str, Any],
                  expected_commit: str, expected_run_id: int) -> dict[str, Any]:
    if (not isinstance(sd_root, Path) or type(expected_commit) is not str or
            type(expected_run_id) is not int or
            not isinstance(receipt, dict) or
            receipt.get("git_commit") != expected_commit or
            receipt.get("github_run_id") != expected_run_id):
        raise _bad()
    try:
        binary_hashes = verify_receipt(bundle, receipt)
        expected = {
            **binary_hashes,
            "switch/foj/gpu/material0.dds": hashlib.sha256(generated_dds(0)).hexdigest(),
            "switch/foj/gpu/material1.dds": hashlib.sha256(generated_dds(1)).hexdigest(),
        }
        first_inventory = _snapshot_foj_tree(sd_root)
        records = []
        for staged, sd_relative, kind in STAGED_FILES:
            data = _read_copied(sd_root, sd_relative, kind)
            digest = hashlib.sha256(data).hexdigest()
            if expected.get(sd_relative) != digest:
                raise _bad()
            records.append({"sd_relative_path": sd_relative, "sha256": digest})
        second_inventory = _snapshot_foj_tree(sd_root)
        if first_inventory != second_inventory:
            raise _bad()
        return {
            "schema": SCHEMA,
            "provenance": "generated-only-readonly-copied-sd-files",
            "git_commit_declared": expected_commit,
            "github_run_id_declared": expected_run_id,
            "bundle_sha256": receipt["bundle_sha256"],
            "sd_copy_files_checked": len(records),
            "sd_copy_matches": True,
            "files": records,
            "physical_switch_execution_verified": False,
            "gpu_scanout_verified": False,
            "original_foj_assets_verified": False,
            "gameplay_verified": False,
        }
    except (OSError, ValueError, KeyError, TypeError):
        raise _bad() from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sd-root", type=Path, required=True,
                        help="Read-only local mounted SD or extracted test tree")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-run-id", type=int, required=True)
    args = parser.parse_args()
    try:
        result = audit_sd_copy(
            args.sd_root, args.bundle, read_receipt(args.receipt),
            args.expected_commit, args.expected_run_id)
    except (ValueError, TypeError, OSError, RecursionError):
        parser.error("Invalid or mismatched generated-only SD research copy")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
