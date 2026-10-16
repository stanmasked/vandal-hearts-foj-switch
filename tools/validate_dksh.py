#!/usr/bin/env python3
"""Validate deko3d DKSH module layout before any user-local GPU shader load.

Grounded in devkitPro/deko3d source/dksh.h:
- 24-byte DkshHeader
- 64-byte DkshProgramHeader for each program
- independent 256-byte-aligned control and code sections

This is a bounded *structure and stage* check, NOT shader ISA validation,
deko3d linkage, UAM toolchain confirmation or actual GPU execution.
Only generated mock DKSH containers are used in repository tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

_HEADER = struct.Struct("<6I")
_PROGRAM_COMMON = struct.Struct("<6I")
DKSH_MAGIC = 0x48534B44
DKSH_PROGRAM_BYTES = 64
DKSH_ALIGNMENT = 256
MAX_DKSH_BYTES = 8 * 1024 * 1024
PROGRAM_TYPES = {
    0: "vertex", 1: "fragment", 2: "geometry",
    3: "tess_control", 4: "tess_evaluation", 5: "compute",
}


class DkshError(ValueError):
    pass


def inspect_dksh(data: bytes, expected_stage: str | None = None) -> dict:
    if (not isinstance(data, bytes) or
            not _HEADER.size <= len(data) <= MAX_DKSH_BYTES):
        raise DkshError("DKSH length outside supported limits")
    if expected_stage is not None and expected_stage not in PROGRAM_TYPES.values():
        raise DkshError("Unknown requested DKSH shader stage")

    magic, header_size, control_size, code_size, programs_offset, count = (
        _HEADER.unpack_from(data)
    )
    if magic != DKSH_MAGIC:
        raise DkshError("Missing DKSH magic")
    if header_size != _HEADER.size:
        raise DkshError("Unexpected DKSH header size (expected 24 bytes)")
    if (control_size < header_size or
            control_size % DKSH_ALIGNMENT != 0 or
            code_size == 0 or code_size % DKSH_ALIGNMENT != 0):
        raise DkshError("Invalid DKSH control/code section alignment")
    if control_size + code_size != len(data):
        raise DkshError("DKSH declared sections do not equal file length")
    if not 1 <= count <= 16:
        raise DkshError("Invalid DKSH program count")
    if (programs_offset < header_size or
            programs_offset % 4 or
            programs_offset + count * DKSH_PROGRAM_BYTES > control_size):
        raise DkshError("DKSH 64-byte program table exceeds control section")

    stages = []
    for index in range(count):
        offset = programs_offset + index * DKSH_PROGRAM_BYTES
        program_type, entrypoint, regs, cb_offset, cb_size, scratch = (
            _PROGRAM_COMMON.unpack_from(data, offset)
        )
        if program_type not in PROGRAM_TYPES:
            raise DkshError(f"Unknown DKSH program type at index {index}")
        if entrypoint >= code_size:
            raise DkshError(f"DKSH entrypoint outside code at index {index}")
        if cb_size and (cb_offset >= code_size or
                        cb_size > code_size - cb_offset):
            raise DkshError(f"DKSH constbuf exceeds code at index {index}")
        stages.append(PROGRAM_TYPES[program_type])
    if expected_stage is not None and (
        count != 1 or stages[0] != expected_stage
    ):
        raise DkshError(
            f"Expected exactly one {expected_stage} DKSH program, got {stages}"
        )
    return {
        "format": "DKSH",
        "total_bytes": len(data),
        "header_bytes": header_size,
        "control_bytes": control_size,
        "code_bytes": code_size,
        "programs_offset": programs_offset,
        "program_count": count,
        "stages": stages,
        "note": (
            "64-byte program records and section bounds checked against "
            "deko3d dksh.h; Maxwell shader instructions, resource bindings "
            "and actual GPU execution remain unverified."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-stage", choices=sorted(PROGRAM_TYPES.values()),
                        help="Require one program of this precise DKSH stage")
    parser.add_argument("files", type=Path, nargs="+",
                        help="Existing compiled deko3d UAM .dksh files")
    args = parser.parse_args(argv)
    for path in args.files:
        try:
            if path.stat().st_size > MAX_DKSH_BYTES:
                raise DkshError("DKSH file too large")
            report = inspect_dksh(
                path.read_bytes(), expected_stage=args.expect_stage
            )
        except (OSError, DkshError) as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({"file": path.name, **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
