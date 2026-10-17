#!/usr/bin/env python3
"""Create TWO deterministic, generated-only DDS files for a Switch GPU smoke.

The output is not FoJ game art; these checkerboards deliberately distinguish
material slot 0 and 1. Creates a new directory exclusively, never edits
private user DDS files and never accesses the Nintendo Switch remotely.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import struct

from tools.foj_gpu_local_dds_preflight import classify_classic_dds, examine_local_slots

SIZE = 8
HEADER_BYTES = 128
SLOTS = ("material0.dds", "material1.dds")


def generated_dds(material_slot: int) -> bytes:
    if type(material_slot) is not int or material_slot not in (0, 1):
        raise ValueError("Synthetic GPU material slot must be 0 or 1")
    dds = bytearray(HEADER_BYTES)
    dds[0:4] = b"DDS "
    for at, value in (
        (4, 124), (8, 0x100f), (12, SIZE), (16, SIZE),
        (20, SIZE * 4), (28, 1), (76, 32), (80, 0x41), (88, 32),
        (92, 0x000000ff), (96, 0x0000ff00), (100, 0x00ff0000),
        (104, 0xff000000), (108, 0x1000),
    ):
        struct.pack_into("<I", dds, at, value)
    for y in range(SIZE):
        for x in range(SIZE):
            checked = (x // 2 + y // 2) % 2
            if material_slot == 0:
                rgba = (240, 45, 30, 255) if checked else (255, 215, 70, 255)
            else:
                rgba = (35, 95, 235, 255) if checked else (70, 235, 220, 255)
            dds.extend(rgba)
    result = bytes(dds)
    classify_classic_dds(result)
    return result


def publish_generated_pair(destination: Path) -> dict:
    if not isinstance(destination, Path):
        raise ValueError("Synthetic output directory must be a Path")
    try:
        destination.mkdir(parents=False, exist_ok=False)
    except OSError:
        raise ValueError("Synthetic output directory must be new and writable") from None
    # If a filesystem write fails, leave the directory for manual inspection
    # rather than deleting or overwriting files in a concurrently changed path.
    try:
        for i, name in enumerate(SLOTS):
            with (destination / name).open("xb") as output:
                output.write(generated_dds(i))
        report = examine_local_slots(destination)
        if [x["status"] for x in report["slots"]] != [
                "classic-dds-compatible"] * 2:
            raise ValueError("Generated pair failed native intake preflight")
        return report
    except OSError:
        raise ValueError("Unable to write the generated DDS pair") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path,
                        help="NEW local directory; for example ./smoke-dds-stage162")
    args = parser.parse_args()
    try:
        report = publish_generated_pair(args.directory)
    except ValueError as exc:
        parser.error(str(exc))
    print("Created two generated-only 8x8 RGBA8 DDS materials.")
    print("Preflight:", ", ".join(x["status"] for x in report["slots"]))
    print("Use only on your own homebrew Switch; these are not FoJ assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
