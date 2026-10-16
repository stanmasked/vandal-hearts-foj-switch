#!/usr/bin/env python3
"""Deterministic devkitPro GPU preflight for the OPTIONAL FoJ deko3d NRO.

No network calls and no original game data. Reports missing native
cross-build prerequisites before invoking make. Existence checks do not
constitute evidence that a linker invocation or GPU frame will succeed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil


def inspect_toolchain(root: Path, devkita64: Path | None = None,
                      *, require_shaders: bool = False,
                      path_lookup=None) -> dict:
    root = Path(root)
    arch = Path(devkita64) if devkita64 is not None else root / "devkitA64"
    lookup = path_lookup if path_lookup is not None else shutil.which

    required = {
        "aarch64_compiler": (arch / "bin/aarch64-none-elf-gcc", True),
        "switch_header": (root / "libnx/include/switch.h", False),
        "deko3d_header": (root / "libnx/include/deko3d.h", False),
        "libnx_archive": (root / "libnx/lib/libnx.a", False),
        "deko3d_debug_archive": (
            root / "libnx/lib/libdeko3dd.a", False
        ),
        "elf2nro": (root / "tools/bin/elf2nro", True),
        "nacptool": (root / "tools/bin/nacptool", True),
    }
    checks = {}
    for name, (path, executable) in required.items():
        exists = path.is_file()
        if exists and executable:
            exists = os.access(path, os.X_OK)
        checks[name] = {
            "path": str(path),
            "available": exists,
            "mandatory": True,
            "kind": "executable" if executable else "file",
        }
    uam_path = lookup("uam") or str(root / "tools/bin/uam")
    uam = Path(uam_path)
    uam_available = uam.is_file() and os.access(uam, os.X_OK)
    checks["uam"] = {
        "path": str(uam),
        "available": uam_available,
        "mandatory": bool(require_shaders),
        "kind": "executable",
    }
    missing = sorted(
        name for name, check in checks.items()
        if check["mandatory"] and not check["available"]
    )
    return {
        "devkitpro": str(root),
        "devkita64": str(arch),
        "requires_uam": require_shaders,
        "ready_for_compile_attempt": not missing,
        "missing_mandatory": missing,
        "checks": checks,
        "qualification": (
            "File presence is not a successful cross-build, shader compile, "
            "NRO boot or physical Nintendo Switch GPU rendering test."
        ),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--devkitpro", type=Path,
                   default=Path(os.environ.get("DEVKITPRO", "/opt/devkitpro")))
    p.add_argument("--devkita64", type=Path,
                   default=Path(os.environ["DEVKITA64"])
                   if os.environ.get("DEVKITA64") else None)
    p.add_argument("--require-shaders", action="store_true",
                   help="Require UAM compiler as well as the clear-only SDK")
    args = p.parse_args(argv)
    report = inspect_toolchain(
        args.devkitpro, args.devkita64,
        require_shaders=args.require_shaders
    )
    print(json.dumps(report, indent=2))
    return 0 if report["ready_for_compile_attempt"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
