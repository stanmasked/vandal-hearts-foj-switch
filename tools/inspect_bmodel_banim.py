#!/usr/bin/env python3
"""Conservative *header-only* research for FoJ .bmodel and .banim resources.

These files contain proprietary game data. This module is not a full parser
and does not export meshes, skeletal tracks or raw game bytes. The labeled
fields are directly grounded observations; their gameplay semantics need
independent validation.
"""
from __future__ import annotations

import math
import struct
from pathlib import Path


class UnsupportedHeader(ValueError):
    pass


def inspect_bmodel(data: bytes) -> dict:
    """Recognize tested model headers; describe ONLY the first named shape."""
    if (len(data) < 10 or data[:3] != b"\x0b\x09\x00" or
        data[4:7] != b"\x01\x20\x00"):
        raise UnsupportedHeader("Unsupported or truncated .bmodel preamble")
    count = data[3]
    name_length = data[7]
    if count < 1 or count > 64 or name_length < 1 or name_length > 127:
        raise UnsupportedHeader("Unexpected .bmodel count/name length")
    if len(data) < 8 + name_length:
        raise UnsupportedHeader("Incomplete first shape name")
    try:
        shape = data[8:8 + name_length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedHeader("Invalid UTF-8 shape name") from exc
    if not all(32 <= ord(ch) <= 126 for ch in shape):
        raise UnsupportedHeader("Non-printable shape name")
    return {
        "file_type": "bmodel",
        "candidate_part_count": count,
        "first_shape_name": shape,
        "first_shape_name_length": name_length,
        "note": "Count/part identity inferred from repeated samples; vertex layout unknown.",
    }


def inspect_banim(data: bytes) -> dict:
    """Recognize candidate animation-duration header, without track decoding."""
    if len(data) < 8 or data[0] != 0x0d:
        raise UnsupportedHeader("Unsupported or truncated .banim preamble")
    duration = struct.unpack_from("<f", data, 1)[0]
    if not (math.isfinite(duration) and 0 < duration <= 600):
        raise UnsupportedHeader("Animation candidate duration out of bounds")
    return {
        "file_type": "banim",
        "candidate_duration_seconds": round(duration, 6),
        "header_variant": data[5],
        "note": "Duration/variant interpretation is provisional; pose tracks unknown.",
    }


def inspect_resource_header(name: str, data: bytes) -> dict:
    extension = Path(name).suffix.lower()
    if extension == ".bmodel":
        return inspect_bmodel(data)
    if extension == ".banim":
        return inspect_banim(data)
    raise UnsupportedHeader("Only .bmodel and .banim supported")
