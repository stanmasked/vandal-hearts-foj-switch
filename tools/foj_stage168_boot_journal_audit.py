#!/usr/bin/env python3
"""Audit a user-copied, PRIVATE GPU boot breadcrumb; no hardware attestation.

Never uploads logs, extracts game data, infers video/GPU success or
prints private source locations. All evidence is CPU-side control flow.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import stat

LINE = re.compile(rb"FOJBOOT1 slot=(0[0-9]|1[0-5]) step=(0[1-9]|10|11) event=([1-4]) frames=([0-9]{10})\n")
BASENAME = re.compile(r"foj-boot-(0[0-9]|1[0-5])\.txt")
STAGES = {
    1: "device", 2: "queue", 3: "framebuffers",
    4: "swapchain", 5: "command_buffer", 6: "vertices",
    7: "shaders", 8: "textures", 9: "command_lists",
    10: "presentation", 11: "exit",
}
MAX_BYTES = 64 * 64


def invalid() -> ValueError:
    return ValueError("Invalid or unstable private GPU boot journal")


def parse_journal(data: bytes, *, expected_slot: int | None = None) -> dict:
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
        raise invalid()
    lines = data.splitlines(keepends=True)
    if not 1 <= len(lines) <= 64:
        raise invalid()
    actual_slot = None
    previous_stage = 0
    previous_frames = 0
    stage_started = False
    exited = False
    latest_event = 0
    latest_stage = 0
    for line in lines:
        match = LINE.fullmatch(line)
        if match is None:
            raise invalid()
        slot, step, event, frame = (
            int(match.group(i)) for i in range(1, 5))
        if actual_slot is None:
            actual_slot = slot
        if slot != actual_slot or (expected_slot is not None and slot != expected_slot):
            raise invalid()
        if frame < previous_frames or exited:
            raise invalid()
        if event == 1:  # enter a new stage
            if step <= previous_stage or step == 11:
                raise invalid()
            previous_stage = step
            stage_started = True
        elif event in (2, 3):  # ready / failed for current stage
            if not stage_started or step != previous_stage:
                raise invalid()
        else:  # exit record must be the last complete record
            if step != 11 or not stage_started:
                raise invalid()
            exited = True
        previous_frames = frame
        latest_stage, latest_event = step, event
    if actual_slot is None:
        raise invalid()
    return {
        "schema": "foj-stage168-local-boot-audit-v1",
        "evidence_level": "CPU checkpoint statements only",
        "hardware_gpu_presentation_verified": False,
        "game_assets_verified": False,
        "slot": actual_slot,
        "records": len(lines),
        "latest_stage": STAGES[latest_stage],
        "latest_event": {1: "entered", 2: "ready", 3: "failed", 4: "exited"}[latest_event],
        "last_reported_present_calls": previous_frames,
        "ended_with_exit_marker": exited,
    }


def read_journal(path: Path) -> dict:
    if not isinstance(path, Path):
        raise invalid()
    match = BASENAME.fullmatch(path.name)
    if match is None:
        raise invalid()
    try:
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode) or not 1 <= meta.st_size <= MAX_BYTES:
            raise invalid()
        with path.open("rb") as f:
            first = f.read(MAX_BYTES + 1)
            f.seek(0)
            second = f.read(MAX_BYTES + 1)
        final = path.lstat()
        if (first != second or len(first) != meta.st_size or
                (meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns,
                 meta.st_ctime_ns) !=
                (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns,
                 final.st_ctime_ns)):
            raise invalid()
    except OSError:
        raise invalid() from None
    return parse_journal(first, expected_slot=int(match.group(1)))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--file", type=Path, required=True,
                   help="PRIVATE copied fixed-format foj-boot-XX.txt")
    args = p.parse_args()
    try:
        report = read_journal(args.file)
    except ValueError as exc:
        p.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
