#!/usr/bin/env python3
"""Stage 176: fd-anchored inventory of downloaded generated-only artifacts.

The snapshot is an unsigned local consistency observation, NOT a
filesystem transaction, GitHub authentication or hardware attestation.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

DIRFLAGS = (os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) |
            getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
MAX_ENTRIES = 24
MAX_NAMES_BYTES = 4096


def _bad() -> ValueError:
    return ValueError("Invalid or changing downloaded research artifact inventory")


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def snapshot_inventory(
    root: Path, allowed_files: frozenset[str], allowed_dirs: frozenset[str],
) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Enumerate one exact file tree without following symlink components.

    Directory opens, stats, and enumeration use held descriptors. The
    returned metadata can be compared before and after the content audit.
    Unlike a signature or an immutable mount, this cannot rule out an
    adversary performing precisely timed reversible ABA modifications.
    """
    if (not isinstance(root, Path) or
            not isinstance(allowed_files, frozenset) or
            not isinstance(allowed_dirs, frozenset) or
            not getattr(os, "O_DIRECTORY", 0) or
            not getattr(os, "O_NOFOLLOW", 0)):
        raise _bad()
    if (not all(isinstance(x, str) and x and not x.startswith("/") and
                ".." not in x.split("/") and "\\" not in x and "\x00" not in x
                for x in allowed_files | allowed_dirs)):
        raise _bad()
    seen_files: set[str] = set()
    seen_dirs: set[str] = set()
    records: list[tuple[str, tuple[int, ...]]] = []
    counts = [0, 0]

    def walk(directory_fd: int, prefix: str) -> None:
        opened_dir = os.fstat(directory_fd)
        # Opening "." makes a new directory description for readdir, so
        # repeat scans are not affected by a previous readdir offset.
        scan_fd = os.open(".", DIRFLAGS, dir_fd=directory_fd)
        try:
            names: list[str] = []
            with os.scandir(scan_fd) as entries:
                for entry in entries:
                    name = entry.name
                    counts[0] += 1
                    counts[1] += len(os.fsencode(name))
                    if (counts[0] > MAX_ENTRIES or
                            counts[1] > MAX_NAMES_BYTES or
                            not name or name in (".", "..") or
                            "/" in name or "\\" in name or "\x00" in name):
                        raise _bad()
                    names.append(name)
        finally:
            os.close(scan_fd)
        if len(names) != len(set(names)):
            raise _bad()
        for name in sorted(names):
            relative = prefix + name
            first = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            identity = _identity(first)
            if stat.S_ISDIR(first.st_mode):
                if relative not in allowed_dirs or relative in seen_dirs:
                    raise _bad()
                seen_dirs.add(relative)
                child_fd = os.open(name, DIRFLAGS, dir_fd=directory_fd)
                try:
                    if _identity(os.fstat(child_fd)) != identity:
                        raise _bad()
                    records.append(("d:" + relative, identity))
                    walk(child_fd, relative + "/")
                    if (_identity(os.fstat(child_fd)) != identity or
                            _identity(os.stat(name, dir_fd=directory_fd,
                                              follow_symlinks=False)) != identity):
                        raise _bad()
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(first.st_mode):
                if relative not in allowed_files or relative in seen_files:
                    raise _bad()
                seen_files.add(relative)
                records.append(("f:" + relative, identity))
                if (_identity(os.stat(name, dir_fd=directory_fd,
                                      follow_symlinks=False)) != identity):
                    raise _bad()
            else:
                raise _bad()
        if _identity(os.fstat(directory_fd)) != _identity(opened_dir):
            raise _bad()

    try:
        initial_root = root.lstat()
        if not stat.S_ISDIR(initial_root.st_mode):
            raise _bad()
        root_fd = os.open(root, DIRFLAGS)
        try:
            if _identity(os.fstat(root_fd)) != _identity(initial_root):
                raise _bad()
            walk(root_fd, "")
            if (_identity(os.fstat(root_fd)) != _identity(initial_root) or
                    _identity(root.lstat()) != _identity(initial_root)):
                raise _bad()
        finally:
            os.close(root_fd)
    except (OSError, ValueError, TypeError, RecursionError):
        raise _bad() from None
    if seen_files != allowed_files or seen_dirs != allowed_dirs:
        raise _bad()
    return tuple(sorted(records))
