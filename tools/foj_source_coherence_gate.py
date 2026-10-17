#!/usr/bin/env python3
"""Bounded local PS3 source-tree coherence gate for DDS metadata research.

Hash user-local regular files *before and after* the whole stage 141-145
pipeline; reject any pathname, inode, metadata or byte-content change.
Nothing is decrypted or uploaded. Fingerprints remain in process memory
and are never included in reports. This catches ordinary mid-run changes,
not a malicious actor capable of modifying files while bypassing checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Any

from tools.foj_texture_probe import (
    DEFAULT_MAX_FILE_BYTES, DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_METADATA_BYTES, inventory,
)
from tools.foj_fd_bound_reader import (
    bounded_directory_names, DEFAULT_MAX_DIR_ENTRIES,
    DEFAULT_MAX_DIR_NAME_BYTES,
)
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import infer_tables
from tools.foj_index_column_controls import analyze_index_columns
from tools.foj_evidence_triage import triage_reports
from tools.foj_report_replay_audit import audit_replay
from tools.foj_report_transit_budget import measure_report

DEFAULT_MAX_TOTAL_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_FILES = 20000
DEFAULT_MAX_BUNDLE_BYTES = 128 * 1024 * 1024
CHUNK = 1024 * 1024
FILE_NAMES = (
    "foj-texture-candidates.json",
    "foj-texture-relations.json",
    "foj-table-hypotheses.json",
    "foj-index-observations.json",
    "foj-evidence-triage.json",
    "foj-report-replay.json",
    "foj-source-coherence.json",
)
FLAGS = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
DIRECTORY = getattr(os, "O_DIRECTORY", 0)
NONBLOCK = getattr(os, "O_NONBLOCK", 0)


def _metadata(st: os.stat_result) -> tuple:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size,
            st.st_mtime_ns, st.st_ctime_ns)


def _identical(a: os.stat_result, b: os.stat_result) -> None:
    if _metadata(a) != _metadata(b):
        raise ValueError("Source changed while it was being examined")


def snapshot(root: Path, *, max_files: int = DEFAULT_MAX_FILES,
             max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
             max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
             max_dir_entries: int = DEFAULT_MAX_DIR_ENTRIES,
             max_dir_name_bytes: int = DEFAULT_MAX_DIR_NAME_BYTES) -> tuple[dict, dict]:
    """Take a bounded, fd-relative, non-symlink, in-memory directory snapshot.

    Reject all non-regular entries, symlinks and unstable reads rather than
    silently skipping them. The return value MUST NOT be serialized/published.
    """
    if (type(max_files) is not int or not 1 <= max_files <= DEFAULT_MAX_FILES or
            type(max_file_bytes) is not int or not 1 <= max_file_bytes <=
            DEFAULT_MAX_FILE_BYTES or
            type(max_total_bytes) is not int or not 1 <= max_total_bytes <=
            64 * DEFAULT_MAX_TOTAL_BYTES):
        raise ValueError("Snapshot limits outside permitted bounds")
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Source root must be a real non-symlink directory")
    if not NOFOLLOW or not DIRECTORY:
        raise ValueError("Platform lacks no-follow directory descriptor support")

    fingerprint: dict[str, tuple] = {}
    totals = {"regular_files": 0, "directories": 0, "bytes_per_pass": 0}
    root_fd = os.open(root, FLAGS | NOFOLLOW | DIRECTORY)

    def visit(directory_fd: int, relative: str) -> None:
        start = os.fstat(directory_fd)
        if not stat.S_ISDIR(start.st_mode):
            raise ValueError("Source directory replaced during scan")
        totals["directories"] += 1
        if totals["directories"] > max_files + 1:
            raise ValueError("Too many source directories for a complete audit")
        names = bounded_directory_names(
            directory_fd, max_entries=max_dir_entries,
            max_name_bytes=max_dir_name_bytes)
        for name in names:
            rel = relative + name
            try:
                initial = os.stat(name, dir_fd=directory_fd,
                                  follow_symlinks=False)
            except OSError:
                raise ValueError("Source entry changed during snapshot") from None
            if stat.S_ISDIR(initial.st_mode):
                child = os.open(name, FLAGS | NOFOLLOW | DIRECTORY,
                                dir_fd=directory_fd)
                try:
                    _identical(initial, os.fstat(child))
                    visit(child, rel + "/")
                    _identical(initial, os.fstat(child))
                finally:
                    os.close(child)
            elif stat.S_ISREG(initial.st_mode):
                totals["regular_files"] += 1
                if totals["regular_files"] > max_files:
                    raise ValueError("Too many source files for a complete audit")
                if (initial.st_size > max_file_bytes or
                        initial.st_size > max_total_bytes -
                        totals["bytes_per_pass"]):
                    raise ValueError("Source tree exceeds byte audit limits")
                fd = os.open(name, FLAGS | NOFOLLOW | NONBLOCK,
                             dir_fd=directory_fd)
                try:
                    opened = os.fstat(fd)
                    _identical(initial, opened)
                    if not stat.S_ISREG(opened.st_mode):
                        raise ValueError("Source file changed type")
                    digest = hashlib.sha256()
                    count = 0
                    while True:
                        chunk = os.read(fd, CHUNK)
                        if not chunk:
                            break
                        count += len(chunk)
                        if count > opened.st_size:
                            raise ValueError("Source grew while being hashed")
                        digest.update(chunk)
                    if count != opened.st_size:
                        raise ValueError("Source size changed while hashing")
                    _identical(opened, os.fstat(fd))
                    fingerprint["F:" + rel] = (_metadata(opened), digest.digest())
                    totals["bytes_per_pass"] += count
                finally:
                    os.close(fd)
            else:
                raise ValueError("Symlink or unsupported source entry detected")
        _identical(start, os.fstat(directory_fd))
        if names != bounded_directory_names(
                directory_fd, max_entries=max_dir_entries,
                max_name_bytes=max_dir_name_bytes):
            raise ValueError("Source directory membership changed during snapshot")
        fingerprint["D:" + relative] = _metadata(start)

    try:
        visit(root_fd, "")
    finally:
        os.close(root_fd)
    return fingerprint, totals


def examine(root: Path, *, max_files: int = DEFAULT_MAX_FILES,
            max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
            max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
            pointer_prefix_bytes: int = 65536,
            control_windows: int = 256,
            max_dir_entries: int = DEFAULT_MAX_DIR_ENTRIES,
            max_dir_name_bytes: int = DEFAULT_MAX_DIR_NAME_BYTES,
            max_candidates: int = DEFAULT_MAX_CANDIDATES,
            max_metadata_bytes: int = DEFAULT_MAX_METADATA_BYTES,
            max_bundle_bytes: int = DEFAULT_MAX_BUNDLE_BYTES) -> tuple[dict[str, Any], ...]:
    """Produce reports only from a source tree stable across two snapshots."""
    before, stats = snapshot(
        root, max_files=max_files, max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes, max_dir_entries=max_dir_entries,
        max_dir_name_bytes=max_dir_name_bytes)
    scan = inventory(root, max_file_bytes=max_file_bytes, max_files=max_files,
                     max_dir_entries=max_dir_entries,
                     max_dir_name_bytes=max_dir_name_bytes,
                     max_candidates=max_candidates,
                     max_metadata_bytes=max_metadata_bytes)
    if (scan["files_scanned"] != stats["regular_files"] or
            scan["skipped_large"] or scan["skipped_links"] or
            scan["scan_truncated_at_file_limit"] or scan.get("read_errors", 0)):
        raise ValueError("DDS scan did not cover the full source snapshot")
    relations = build_relations(
        scan, root=root, prefix_bytes=pointer_prefix_bytes)
    tables = infer_tables(relations)
    indices = analyze_index_columns(
        tables, root=root, prefix_bytes=pointer_prefix_bytes,
        max_control_windows=control_windows)
    triage = triage_reports(relations, tables, indices)
    after, final_stats = snapshot(
        root, max_files=max_files, max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes, max_dir_entries=max_dir_entries,
        max_dir_name_bytes=max_dir_name_bytes)
    if before != after or stats != final_stats:
        raise ValueError("Source tree changed between DDS pipeline stages")
    replay = audit_replay(relations, tables, indices, triage)
    final = {
        "schema": "foj-source-coherence-gate-v1",
        "status": "two-snapshots-match",
        "note": ("Same local source tree at two boundaries; fingerprints "
                 "not exported, no adversarial TOCTOU or provenance guarantee"),
        "summary": {
            **stats,
            "dds_candidates": len(scan["candidates"]),
            "hypothetical_tables": triage["summary"]["tables_examined"],
            "internally_contradicted":
                triage["summary"]["internally_contradicted"],
            "replay_verified": replay["status"] == "internally-replayed",
            "original_foj_format_proven": False,
            "switch_hardware_verified": False,
        },
    }
    if (type(max_bundle_bytes) is not int or
            not 1024 <= max_bundle_bytes <= 256 * 1024 * 1024):
        raise ValueError("Invalid local report bundle byte budget")
    reports = (scan, relations, tables, indices, triage, replay, final)
    total = 0
    for report in reports:
        total += measure_report(report)
        if total > max_bundle_bytes:
            raise ValueError("Private report bundle byte budget exceeded")
    return reports


def publish(root: Path, output_dir: Path, **limits: Any) -> dict[str, Any]:
    """Write a brand-new output directory only after successful verification."""
    root_real = root.resolve()
    target = output_dir.resolve(strict=False)
    if target == root_real or root_real in target.parents:
        raise ValueError("Output directory must be outside the source tree")
    if output_dir.is_symlink() or output_dir.exists():
        raise ValueError("Output directory must not already exist")
    reports = examine(root, **limits)
    # Publication is deliberately AFTER the entire pipeline/snapshot gate.
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=".foj-stage150-", dir=str(output_dir.parent)))
    try:
        for filename, report in zip(FILE_NAMES, reports):
            file = staging / filename
            with file.open("w", encoding="utf-8") as stream:
                json.dump(report, stream, sort_keys=True, indent=2,
                          ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
        os.replace(staging, output_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return reports[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path,
                        help="Privately extracted, non-symlink PS3 resource tree")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="NEW local report directory outside the source tree")
    parser.add_argument("--total-mib", type=int, default=1024,
                        help="Maximum source bytes per snapshot, default 1024 MiB")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--file-mib", type=int, default=512)
    parser.add_argument("--bundle-mib", type=int, default=128)
    parser.add_argument("--max-candidates", type=int,
                        default=DEFAULT_MAX_CANDIDATES)
    parser.add_argument("--max-metadata-mib", type=int, default=8)
    parser.add_argument("--max-dir-entries", type=int,
                        default=DEFAULT_MAX_DIR_ENTRIES)
    parser.add_argument("--max-dir-name-bytes", type=int,
                        default=DEFAULT_MAX_DIR_NAME_BYTES)
    args = parser.parse_args()
    try:
        result = publish(
            args.root, args.output_dir,
            max_files=args.max_files,
            max_candidates=args.max_candidates,
            max_bundle_bytes=args.bundle_mib * 1024 * 1024,
            max_metadata_bytes=args.max_metadata_mib * 1024 * 1024,
            max_file_bytes=args.file_mib * 1024 * 1024,
            max_total_bytes=args.total_mib * 1024 * 1024,
            max_dir_entries=args.max_dir_entries,
            max_dir_name_bytes=args.max_dir_name_bytes)
    except OSError as exc:
        # OSError strings can include private source filenames: redact them.
        parser.error("Source coherence gate failed: local I/O error (" +
                     type(exc).__name__ + ")")
    except (ValueError, TypeError) as exc:
        parser.error("Source coherence gate failed: " + str(exc))
    print("Source coherence verified:",
          result["summary"]["regular_files"],
          "local files,",
          result["summary"]["dds_candidates"],
          "DDS header candidates; no FoJ format proven")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
