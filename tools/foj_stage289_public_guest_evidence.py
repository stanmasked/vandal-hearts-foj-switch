#!/usr/bin/env python3
"""Stage289: fail-closed publication boundary for Stage288 generated-only GPU evidence.

The NeXium runner may retain raw guest logs for local diagnosis, but the
public artifact contains only independently audited, explicit evidence files.
Never use this with private game inputs. In particular, a failed audit must
not result in a best-effort upload of the unfiltered source tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from tools.foj_stage288_generated_bridge_gpu import audit

SCHEMA = "foj.stage289.verified_guest_evidence_export.v1"
RECEIPT = "stage288-three-dds-gpu-receipt.json"
PUBLIC_BRIDGE_FILES = (
    "generated-input.json",
    "dds-before.json",
    "dds-after.json",
    "gpu-initial.png",
    "gpu-later.png",
    "native-sort-pass.txt",
    "native-alpha-pass.txt",
    RECEIPT,
)
PRIVATE_RUNNER_ONLY = ("guest.log",)
ARCHIVE_HASH = "nexium-archive.sha256"
MAX_FILE = {
    "gpu-initial.png": 12 * 1024 * 1024,
    "gpu-later.png": 12 * 1024 * 1024,
    "guest.log": 4 * 1024 * 1024,
}
SOURCE_FILES = {ARCHIVE_HASH} | {
    "bridge/" + name for name in (*PUBLIC_BRIDGE_FILES, *PRIVATE_RUNNER_ONLY)
}
EXPORT_FILES = {ARCHIVE_HASH} | {
    "bridge/" + name for name in PUBLIC_BRIDGE_FILES
}


def _regular_file(path: Path, max_bytes: int = 65536) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage289 refuses missing or linked evidence")
    if not 1 <= path.stat().st_size <= max_bytes:
        raise ValueError("Stage289 evidence exceeds per-file bound")
    return path.read_bytes()


def _check_tree(root: Path, expected: set[str]) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Stage289 evidence root must be an ordinary directory")
    found = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError("Stage289 refuses evidence symlink")
        if path.is_dir():
            if relative != "bridge":
                raise ValueError("Stage289 refuses unexpected evidence directory")
        elif path.is_file():
            max_bytes = MAX_FILE.get(path.name, 65536)
            _regular_file(path, max_bytes)
            found.add(relative)
        else:
            raise ValueError("Stage289 refuses special evidence entry")
    if found != expected:
        raise ValueError("Stage289 unexpected, missing or potentially private evidence file")


def publish(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    if (source.is_symlink() or not source.is_dir() or
            output.exists() or output.is_symlink() or
            not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage289 requires an existing source and fresh publication root")
    # All source paths are enumerated before any copy is made.
    _check_tree(source, SOURCE_FILES)
    original = audit(source / "bridge")
    saved = json.loads(_regular_file(source / "bridge" / RECEIPT))
    if original != saved:
        raise ValueError("Stage289 Stage288 signed-off report differs from recomputed audit")
    archive = _regular_file(source / ARCHIVE_HASH)
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n", archive):
        raise ValueError("Stage289 malformed NeXium archive provenance")
    hashes = {}
    output.mkdir(mode=0o700)
    try:
        (output / "bridge").mkdir(mode=0o700)
        for relative in sorted(EXPORT_FILES):
            incoming = source / relative
            payload = _regular_file(incoming, MAX_FILE.get(incoming.name, 65536))
            hashes[relative] = hashlib.sha256(payload).hexdigest()
            target = output / relative
            with target.open("xb") as stream:
                stream.write(payload)
            if _regular_file(target, MAX_FILE.get(target.name, 65536)) != payload:
                raise ValueError("Stage289 publication copy mismatched source")
        _check_tree(output, EXPORT_FILES)
        if audit(output / "bridge") != original:
            raise ValueError("Stage289 staged public audit differs from source")
        for relative, checksum in hashes.items():
            if hashlib.sha256(_regular_file(source / relative,
                            MAX_FILE.get(Path(relative).name, 65536))).hexdigest() != checksum:
                raise ValueError("Stage289 source changed during publication")
    except BaseException:
        import shutil
        shutil.rmtree(output)
        raise
    return {
        "schema": SCHEMA,
        "generated_only": True,
        "original_ps3_resources": False,
        "physical_switch_verified": False,
        "neixum_guest_frames_audited": original["verified_guest_frames"],
        "public_files": len(EXPORT_FILES),
        "raw_guest_log_uploaded": False,
        "private_manifest_uploaded": False,
        "strict_source_allowlist_checked": True,
        "strict_export_allowlist_checked": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = publish(args.source, args.output)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        print("Stage289 evidence publication refused; no raw evidence tree is uploaded.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
