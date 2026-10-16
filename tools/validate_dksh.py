#!/usr/bin/env python3
"""Validate *structural* deko3d DKSH files after native UAM compilation.

This is a defensive offline DKSH container inspector, not a GPU ISA parser
or a substitute for running shaders on Nintendo Switch. Synthetic fixtures
used by CI have no Nintendo/publisher binary payload.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

_HEADER = struct.Struct("<6I")
DKSH_MAGIC = 0x48534B44
MAX_DKSH_BYTES = 8 * 1024 * 1024


class DkshError(ValueError):
    pass


def inspect_dksh(data: bytes) -> dict:
    if not isinstance(data, bytes) or not _HEADER.size <= len(data) <= MAX_DKSH_BYTES:
        raise DkshError("DKSH length outside supported limits")
    magic, header_size, control_size, code_size, programs_offset, count = (
        _HEADER.unpack_from(data)
    )
    if magic != DKSH_MAGIC:
        raise DkshError("Missing DKSH magic")
    if not (_HEADER.size <= header_size <= 4096):
        raise DkshError("Invalid DKSH header size")
    if (control_size < header_size or control_size % 256 != 0 or
            code_size == 0 or code_size % 256 != 0):
        raise DkshError("Invalid DKSH control/code section alignment")
    if control_size + code_size != len(data):
        raise DkshError("DKSH declared sections do not equal file length")
    if not 1 <= count <= 16:
        raise DkshError("Invalid DKSH program count")
    if programs_offset < header_size or programs_offset >= control_size:
        raise DkshError("Invalid DKSH program table offset")
    return {
        "format": "DKSH",
        "total_bytes": len(data),
        "header_bytes": header_size,
        "control_bytes": control_size,
        "code_bytes": code_size,
        "programs_offset": programs_offset,
        "program_count": count,
        "note": (
            "Structural container checks only; Maxwell shader instructions, "
            "UAM stage, descriptor compatibility and GPU execution unverified."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", type=Path, nargs="+",
                        help="Existing compiled deko3d UAM .dksh files")
    args = parser.parse_args(argv)
    for path in args.files:
        try:
            if path.stat().st_size > MAX_DKSH_BYTES:
                raise DkshError("DKSH file too large")
            report = inspect_dksh(path.read_bytes())
        except (OSError, DkshError) as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({"file": path.name, **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
