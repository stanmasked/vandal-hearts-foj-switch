#!/usr/bin/env python3
"""Install Stage341's isolated, source-safe NeXium display configuration.

NeXium's default enabled 26 px game bar shrinks its letterboxed render area.
These settings control only a new per-run NEXIUM_DATA_ROOT/app.json, never a
personal NeXium profile, guest game assets, or raw screenshots.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat

SETTINGS = {
    "log_level": "Info",
    "aspect": "Letterbox",
    "filter": "Nearest",
    "game_bar": False,
}
MAX_BYTES = 512


def verify(root: Path) -> Path:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Stage341 NeXium data root must be a regular directory")
    path = root / "app.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage341 isolated NeXium settings missing or unsafe")
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o077:
        raise ValueError("Stage341 NeXium settings must be owner-only")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Stage341 NeXium settings oversized")
    if json.loads(path.read_text(encoding="utf-8")) != SETTINGS:
        raise ValueError("Stage341 NeXium display settings have changed")
    return path


def install(root: Path) -> Path:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Stage341 NeXium data root must be an existing directory")
    path = root / "app.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(SETTINGS, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return verify(root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "install":
            install(args.root)
        else:
            verify(args.root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print("STAGE341_ISOLATED_NEXIUM_DISPLAY_CONFIG_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
