#!/usr/bin/env python3
"""Fd-relative read-only access to private FoJ research inputs.

All path components are opened relative to an already opened directory
descriptor, without following symbolic links. The final regular file is
checked before and after use, detecting normal in-place edits/replacements.
This does not freeze source bytes against a malicious concurrent writer.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Iterator

READ = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
DIRECTORY = getattr(os, "O_DIRECTORY", 0)
NONBLOCK = getattr(os, "O_NONBLOCK", 0)


def _relative_parts(raw: str | PurePosixPath) -> tuple[str, ...]:
    if not isinstance(raw, (str, PurePosixPath)):
        raise ValueError("Source path must be relative")
    name = str(raw)
    if not name or "\\" in name or "\x00" in name or name.startswith("/"):
        raise ValueError("Invalid relative source path")
    parts = tuple(name.split("/"))
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Untrusted source path component")
    return parts


def _identity(st: os.stat_result) -> tuple[int, ...]:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size,
            st.st_mtime_ns, st.st_ctime_ns)


@contextmanager
def open_regular_beneath(
    root: Path, relative: str | PurePosixPath,
) -> Iterator[tuple[object, os.stat_result]]:
    """Open a regular file safely beneath a non-symlink root.

    The source cannot be substituted with a symlink while traversing it:
    O_NOFOLLOW applies at every os.open() step, including the final file.
    File descriptor identity and metadata remain checked until the caller
    exits the context. File contents are not copied or returned in reports.
    """
    if not NOFOLLOW or not DIRECTORY:
        raise ValueError("Platform lacks required no-follow directory support")
    parts = _relative_parts(relative)
    if not isinstance(root, Path):
        raise ValueError("Source root must be a local Path")
    held = []
    try:
        try:
            directory = os.open(root, READ | NOFOLLOW | DIRECTORY)
        except OSError:
            raise ValueError("Unable to safely open source root") from None
        held.append(directory)
        for part in parts[:-1]:
            try:
                next_fd = os.open(
                    part, READ | NOFOLLOW | DIRECTORY, dir_fd=directory)
            except OSError:
                raise ValueError("Unable to safely open source directory") from None
            held.append(next_fd)
            directory = next_fd
            if not stat.S_ISDIR(os.fstat(directory).st_mode):
                raise ValueError("Source directory is not a directory")
        try:
            file_fd = os.open(
                parts[-1], READ | NOFOLLOW | NONBLOCK, dir_fd=directory)
        except OSError:
            raise ValueError("Unable to safely open regular source file") from None
        held.append(file_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Source entry is not a regular file")
        with os.fdopen(file_fd, "rb", closefd=False) as reader:
            try:
                yield reader, before
            finally:
                if _identity(before) != _identity(os.fstat(file_fd)):
                    raise ValueError("Source file changed while being read")
    finally:
        for fd in reversed(held):
            os.close(fd)


def read_bounded_prefix(root: Path, relative: str | PurePosixPath,
                        limit: int) -> bytes:
    """Return <=limit bytes from the already anchored regular-file descriptor."""
    if type(limit) is not int or not 0 <= limit <= 1024 * 1024:
        raise ValueError("Invalid bounded prefix length")
    with open_regular_beneath(root, relative) as (stream, _):
        return stream.read(limit)
