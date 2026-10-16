#!/usr/bin/env python3
"""Bounded, text-only research of FoJ *.coll, *.vis and *.ini map files.

Parses game files already available *in memory* through the local PSARC reader.
Reports only aggregate structural data; no original map content is written.
Field semantics that are not established are intentionally left unassigned.
"""
from __future__ import annotations

import csv
import io
import math
import re

MAX_TEXT_BYTES = 8_000_000
MAX_GRID_CELLS = 65_536
MAP_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


class MapFormatError(ValueError):
    pass


def _lines(data: bytes) -> list[list[str]]:
    if len(data) > MAX_TEXT_BYTES:
        raise MapFormatError("Map data exceeds inspection limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise MapFormatError("Map text is not UTF-8") from exc
    return list(csv.reader(io.StringIO(text, newline="")))


def _float(value: str) -> float:
    try:
        num = float(value.strip())
    except ValueError as exc:
        raise MapFormatError("Invalid map numeric field") from exc
    if not math.isfinite(num):
        raise MapFormatError("Non-finite map numeric field")
    return num


def _int(value: str) -> int:
    try:
        number = int(value.strip())
    except ValueError as exc:
        raise MapFormatError("Invalid map grid coordinate") from exc
    return number


def _bool(value: str) -> bool:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    raise MapFormatError("Unexpected map boolean field")


def _trim_empty_tail(row: list[str]) -> list[str]:
    return row[:-1] if row and row[-1] == "" else row


def summarize_collision(data: bytes) -> dict:
    rows = _lines(data)
    if not rows:
        raise MapFormatError("Empty collision grid")
    header = _trim_empty_tail(rows[0])
    if len(header) != 6:
        raise MapFormatError("Collision header must have 6 fields")
    width, height = _int(header[0]), _int(header[1])
    if (width <= 0 or height <= 0 or width * height > MAX_GRID_CELLS):
        raise MapFormatError("Collision dimensions outside safety limit")
    origin = [_float(header[2]), _float(header[3])]
    step = [_float(header[4]), _float(header[5])]
    if any(abs(x) < 1e-12 for x in step):
        raise MapFormatError("Zero collision grid step")
    if len(rows) != 1 + width * height:
        raise MapFormatError("Collision row count differs from grid size")

    flag_true_counts = [0, 0]
    nonzero_cells = 0
    varied_samples = 0
    minimum = float("inf")
    maximum = -float("inf")
    for cell_index, row in enumerate(rows[1:]):
        values = _trim_empty_tail(row)
        if len(values) != 8:
            raise MapFormatError("Collision cell must have 8 fields")
        x, y = _int(values[0]), _int(values[1])
        if x != cell_index % width or y != cell_index // width:
            raise MapFormatError("Collision cells out of row-major order")
        samples = [_float(x) for x in values[2:6]]
        minimum = min(minimum, *samples)
        maximum = max(maximum, *samples)
        if any(v != 0 for v in samples):
            nonzero_cells += 1
        if max(samples) != min(samples):
            varied_samples += 1
        for i, value in enumerate(values[6:8]):
            flag_true_counts[i] += _bool(value)

    return {
        "width": width,
        "height": height,
        "cells": width * height,
        "grid_origin": origin,
        "grid_step": step,
        "sample_min": minimum,
        "sample_max": maximum,
        "cells_with_nonzero_samples": nonzero_cells,
        "cells_with_varied_samples": varied_samples,
        "flag_true_counts": flag_true_counts,
        "note": "Four numeric samples and two booleans per tile; semantics unconfirmed.",
    }


def summarize_visibility(data: bytes) -> dict:
    rows = _lines(data)
    if len(rows) < 3:
        raise MapFormatError("Visibility header incomplete")
    if any(len(row) != 1 for row in rows[:3]):
        raise MapFormatError("Visibility header must contain three integer lines")
    version, mode, count = [_int(row[0]) for row in rows[:3]]
    if count < 0 or count > MAX_GRID_CELLS:
        raise MapFormatError("Visibility count outside safety limit")
    if len(rows) - 3 != count:
        raise MapFormatError("Visibility row count mismatch")
    widths: dict[int, int] = {}
    for row in rows[3:]:
        if len(row) < 3:
            raise MapFormatError("Malformed visibility record")
        widths[len(row)] = widths.get(len(row), 0) + 1
    return {
        "version_field": version, "mode_field": mode,
        "records": count, "column_count_histogram": widths,
        "note": "Visibility schema not yet reverse-engineered.",
    }


def summarize_placement(data: bytes) -> dict:
    if len(data) > MAX_TEXT_BYTES:
        raise MapFormatError("INI size outside safety limit")
    text = data.decode("utf-8-sig")
    sections = []
    keys: dict[str, int] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            sections.append(line[1:-1])
        elif "=" in line and not line.startswith(("#", ";")):
            key = line.split("=", 1)[0].strip().lower()
            if key:
                keys[key] = keys.get(key, 0) + 1
    return {
        "section_count": len(sections),
        "placement_property_keys": dict(sorted(keys.items())),
        "note": "Counts only; original placement values omitted.",
    }


def validate_map_name(name: str) -> str:
    if not MAP_NAME.fullmatch(name):
        raise MapFormatError("Map identifier must contain only letters, numbers, _ or -")
    return name
