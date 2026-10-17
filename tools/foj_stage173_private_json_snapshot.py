#!/usr/bin/env python3
"""Stable, bounded descriptor snapshot for private operator-authored JSON.

This protects against ordinary final-path substitutions and in-place
modification. It neither authenticates an operator nor verifies GPU scanout.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat


def _invalid() -> ValueError:
    return ValueError("Invalid or unstable private operator JSON input")


def _identity(meta: os.stat_result) -> tuple[int, ...]:
    return (meta.st_dev, meta.st_ino, meta.st_mode, meta.st_size,
            meta.st_mtime_ns, meta.st_ctime_ns)


def read_private_json_bytes(path: Path, max_bytes: int) -> bytes:
    """Read one regular file twice on the same no-follow descriptor.

    Initial and final pathname metadata must match opened and final
    descriptor metadata. Reject the input if any bytes differ.
    No input bytes, contents, or private path appear in raised errors.
    Does not guard against adversarial ancestor swaps, ABA edits, or
    a malicious filesystem presenting false metadata.
    """
    if (not isinstance(path, Path) or type(max_bytes) is not int or
            not 2 <= max_bytes <= 1024 * 1024):
        raise _invalid()
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if not nofollow:
        raise _invalid()
    try:
        initial = path.lstat()
        if not stat.S_ISREG(initial.st_mode) or not 2 <= initial.st_size <= max_bytes:
            raise _invalid()
        flags = (os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0) |
                 getattr(os, "O_CLOEXEC", 0))
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            opened = os.fstat(stream.fileno())
            first = stream.read(max_bytes + 1)
            stream.seek(0)
            second = stream.read(max_bytes + 1)
            final = os.fstat(stream.fileno())
        named = path.lstat()
        if (_identity(initial) != _identity(opened) or
                _identity(opened) != _identity(final) or
                _identity(final) != _identity(named) or
                len(first) != initial.st_size or first != second):
            raise _invalid()
        return first
    except (OSError, ValueError):
        raise _invalid() from None
