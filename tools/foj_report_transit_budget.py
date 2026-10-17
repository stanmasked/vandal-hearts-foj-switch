#!/usr/bin/env python3
"""Bounded, local-only metadata report transfer between FoJ research stages.

A report is *not* source evidence: this verifies byte budgets and JSON
structure, not game formats or PS3 content authenticity. Nothing is uploaded.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any

MAX_REPORT_BYTES = 64 * 1024 * 1024
READ_FLAGS = (os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) |
              getattr(os, "O_NOFOLLOW", 0) |
              getattr(os, "O_NONBLOCK", 0))


def _valid_limit(limit: int) -> None:
    if type(limit) is not int or not 1024 <= limit <= MAX_REPORT_BYTES:
        raise ValueError("Invalid local report byte budget")


def measure_report(report: dict[str, Any], *,
                   limit: int = MAX_REPORT_BYTES) -> int:
    """Count exact pretty-printed UTF-8 output before downstream consumers.

    Uses JSONEncoder.iterencode so it does not construct an entire second
    report in memory merely to check its encoded size. Almost all JSON
    structural fragments and generated research metadata are ASCII; count
    their characters directly without constructing temporary UTF-8 bytes.
    Non-ASCII fragments still require exact UTF-8 byte measurement.
    A single enormous input scalar is still limited by Python's encoder.
    """
    _valid_limit(limit)
    if not isinstance(report, dict):
        raise ValueError("Expected a metadata JSON object")
    encoded = json.JSONEncoder(
        sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    count = 1  # final newline used by the CLI/published report
    try:
        for fragment in encoded.iterencode(report):
            # Encoding ASCII only to calculate its length creates a bytes
            # allocation per token. isascii() preserves byte-exact counting
            # for escaped JSON strings, punctuation, spaces and numbers.
            # Non-ASCII strings need the real UTF-8 length: code points
            # occupy between 2 and 4 bytes, not one byte per character.
            count += (len(fragment) if fragment.isascii()
                      else len(fragment.encode("utf-8")))
            if count > limit:
                raise ValueError("Local research report byte budget exceeded")
    except UnicodeError:
        # A surrogate-escaped local filename is not valid UTF-8 JSON.
        # Reject without echoing private filesystem or source content.
        raise ValueError("Invalid UTF-8 in local metadata report") from None
    except (OverflowError, RecursionError):
        raise ValueError("Invalid nested local report") from None
    return count


def _unique_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON member in local report")
        result[name] = value
    return result


def read_report(path: Path, *, limit: int = MAX_REPORT_BYTES) -> dict[str, Any]:
    """Read one bounded local JSON report through a no-follow file descriptor.

    Check size before allocating the payload buffer, and check inode,
    timestamps, and byte count after the read. Paths, contents and hashes
    are never copied into exceptions or generated reports.
    """
    _valid_limit(limit)
    if not isinstance(path, Path):
        raise ValueError("Local report path must be a Path")
    if path.is_symlink():
        raise ValueError("Report must be a regular non-symlink local file")
    if not getattr(os, "O_NOFOLLOW", 0):
        raise ValueError("Platform lacks no-follow local report support")
    try:
        fd = os.open(path, READ_FLAGS)
    except OSError:
        raise ValueError("Unable to open local metadata report") from None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Local metadata report is not regular")
        if not 2 <= before.st_size <= limit:
            raise ValueError("Local report input byte budget exceeded")
        with os.fdopen(fd, "rb", closefd=False) as reader:
            data = reader.read(limit + 1)
        after = os.fstat(fd)
        stamps = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_size,
                             st.st_mtime_ns, st.st_ctime_ns)
        if (len(data) != before.st_size or len(data) > limit or
                stamps(before) != stamps(after)):
            raise ValueError("Local metadata report changed during read")
        try:
            report = json.loads(data.decode("utf-8"),
                                object_pairs_hook=_unique_members,
                                parse_constant=lambda _: (_ for _ in ()).throw(
                                    ValueError("Non-finite JSON number")))
        except (UnicodeError, json.JSONDecodeError, RecursionError):
            raise ValueError("Invalid local report JSON") from None
        if not isinstance(report, dict):
            raise ValueError("Expected a metadata JSON object")
        # The decoded report must remain inside the same bounded canonical
        # representation before any stage starts processing it.
        measure_report(report, limit=limit)
        return report
    finally:
        os.close(fd)
