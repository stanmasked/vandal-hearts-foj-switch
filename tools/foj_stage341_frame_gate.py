#!/usr/bin/env python3
"""Stage341 strict CPU oracle for two real NeXium frames sampling one DDS."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import shutil
from pathlib import Path

from PIL import Image

SCHEMA = "foj.stage341.private_dds_frame_audit.v1"
GENERATED_SCHEMA = "foj.stage340.generated_bgra8_dds_fixture.v1"
READY_MARKER = (
    b"FOJ_STAGE341_PRIVATE_DDS_FRAME_READY_V1 width=256 height=256 "
    b"native_upload=1 presented_frames=2\n"
)
FRAMES = ("gpu-initial.png", "gpu-later.png")
WIDTH, HEIGHT = 1280, 720
QUAD_MIN, QUAD_MAX = -0.82, 0.82
TOLERANCE = 10
SAMPLE_POINTS = (
    ("nw", 200, 150),
    ("north_mid", 640, 150),
    ("center", 640, 360),
    ("south_mid", 640, 570),
    ("se", 1080, 600),
)
EVIDENCE_FILES = {
    "source-before.sha256",
    "source-after.sha256",
    "ready-marker.txt",
    "gpu-initial.png",
    "gpu-later.png",
    "guest.log",
    "nexium-archive.sha256",
}


def _regular(path: Path, limit: int) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage341 expected a regular evidence file")
    if path.stat().st_size > limit:
        raise ValueError("Stage341 evidence file exceeds its bound")
    return path.read_bytes()


def _sha(path: Path) -> str:
    return hashlib.sha256(_regular(path, 2 * 1024 * 1024)).hexdigest()


def _hash_file(path: Path) -> str:
    raw = _regular(path, 256).decode("ascii", errors="strict").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", raw):
        raise ValueError("Stage341 checksum file is not a strict SHA-256")
    return raw


def _check_tree(folder: Path, generated_only: bool) -> None:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage341 evidence folder invalid")
    allowed = set(EVIDENCE_FILES)
    if generated_only:
        allowed.add("generated-input.json")
    actual: set[str] = set()
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise ValueError("Stage341 refuses symlinks in evidence")
        if path.is_file():
            actual.add(path.relative_to(folder).as_posix())
        elif not path.is_dir():
            raise ValueError("Stage341 refuses special evidence files")
    if actual != allowed:
        raise ValueError("Stage341 evidence tree differs from strict allowlist")


def _decode_source(path: Path) -> tuple[bytes, bytes]:
    blob = _regular(path, 1024 * 1024)
    if len(blob) != 262272 or blob[:4] != b"DDS ":
        raise ValueError("Stage341 source is not a bounded classic 256x256 DDS")
    try:
        with Image.open(io.BytesIO(blob)) as image:
            if image.format != "DDS" or image.size != (256, 256):
                raise ValueError("Stage341 source dimensions/format mismatch")
            rgba = image.convert("RGBA").tobytes()
    except (OSError, ValueError) as exc:
        raise ValueError("Stage341 Pillow CPU reference decode failed") from exc
    if len(rgba) != 256 * 256 * 4:
        raise ValueError("Stage341 CPU reference has the wrong RGBA byte count")
    return blob, rgba


def _quad_uv(x: int, y: int) -> tuple[float, float]:
    left = (1.0 + QUAD_MIN) * WIDTH / 2.0
    right = (1.0 + QUAD_MAX) * WIDTH / 2.0
    top = (1.0 - QUAD_MAX) * HEIGHT / 2.0
    bottom = (1.0 - QUAD_MIN) * HEIGHT / 2.0
    u = (x + 0.5 - left) / (right - left)
    v = (y + 0.5 - top) / (bottom - top)
    if not (0.0 < u < 1.0 and 0.0 < v < 1.0):
        raise ValueError("Stage341 oracle point lies outside the textured quad")
    return u, v


def _bilinear_rgb(rgba: bytes, u: float, v: float) -> list[int]:
    # Standard normalized texture sampling: texel coordinate = UV * extent - 0.5.
    tx = u * 256.0 - 0.5
    ty = v * 256.0 - 0.5
    x0, y0 = math.floor(tx), math.floor(ty)
    fx, fy = tx - x0, ty - y0

    def channel(x: int, y: int, c: int) -> int:
        xx = min(255, max(0, x))
        yy = min(255, max(0, y))
        return rgba[(yy * 256 + xx) * 4 + c]

    out = []
    for c in range(3):
        p00 = channel(x0, y0, c)
        p10 = channel(x0 + 1, y0, c)
        p01 = channel(x0, y0 + 1, c)
        p11 = channel(x0 + 1, y0 + 1, c)
        top = p00 * (1.0 - fx) + p10 * fx
        bottom = p01 * (1.0 - fx) + p11 * fx
        out.append(int(math.floor(top * (1.0 - fy) + bottom * fy + 0.5)))
    return out


def _frame_samples(path: Path, rgba: bytes) -> tuple[dict, tuple[int, int, int]]:
    data = _regular(path, 12 * 1024 * 1024)
    try:
        with Image.open(io.BytesIO(data)) as opened:
            image = opened.convert("RGB")
    except (OSError, ValueError) as exc:
        raise ValueError("Stage341 screenshot decode failed") from exc
    if image.size != (WIDTH, HEIGHT):
        raise ValueError("Stage341 screenshot is not a 1280x720 NeXium window")
    pixels = image.load()
    samples = {}
    for name, x, y in SAMPLE_POINTS:
        u, v = _quad_uv(x, y)
        expected = _bilinear_rgb(rgba, u, v)
        observed = list(pixels[x, y])
        delta = [abs(observed[c] - expected[c]) for c in range(3)]
        if max(delta) > TOLERANCE:
            raise ValueError(
                f"Stage341 sample {name} exceeded RGB tolerance {TOLERANCE}"
            )
        samples[name] = {
            "xy": [x, y],
            "uv": [round(u, 8), round(v, 8)],
            "expected_rgb": expected,
            "observed_rgb": observed,
            "max_channel_delta": max(delta),
        }
    # The inset quad leaves the alternating clear-color border visible.
    border = tuple(pixels[20, 20])
    return samples, border


def _valid_generated_input(path: Path, source_hash: str, source_bytes: int) -> dict:
    value = json.loads(_regular(path, 4096).decode("utf-8"))
    expected = {
        "schema": GENERATED_SCHEMA,
        "generated_only": True,
        "original_ps3_assets_used": False,
        "physical_switch_verified": False,
        "width": 256,
        "height": 256,
        "format": "BGRA8",
        "dds_file_bytes": source_bytes,
        "sha256": source_hash,
    }
    if any(value.get(key) != expected_value
           for key, expected_value in expected.items()):
        raise ValueError("Stage341 generated-only source provenance mismatch")
    return value


def audit(source_dds: Path, evidence: Path, generated_only: bool = False) -> dict:
    source_dds, evidence = Path(source_dds), Path(evidence)
    _check_tree(evidence, generated_only)
    blob, rgba = _decode_source(source_dds)
    source_hash = hashlib.sha256(blob).hexdigest()
    before = _hash_file(evidence / "source-before.sha256")
    after = _hash_file(evidence / "source-after.sha256")
    if before != after or after != source_hash:
        raise ValueError("Stage341 source changed or does not match staged input hash")
    marker = _regular(evidence / "ready-marker.txt", 512)
    if marker != READY_MARKER:
        raise ValueError("Stage341 native frame-ready marker mismatch")
    _hash_file(evidence / "nexium-archive.sha256")
    _regular(evidence / "guest.log", 4 * 1024 * 1024)
    if generated_only:
        _valid_generated_input(evidence / "generated-input.json",
                               source_hash, len(blob))
    initial, border_initial = _frame_samples(evidence / FRAMES[0], rgba)
    later, border_later = _frame_samples(evidence / FRAMES[1], rgba)
    reference_colors = {
        tuple(initial[name]["expected_rgb"]) for name, _, _ in SAMPLE_POINTS
    }
    if len(reference_colors) < 3:
        raise ValueError("Stage341 sample coordinates do not distinguish the source texture")
    if border_initial == border_later:
        raise ValueError("Stage341 captures are stale/duplicate at the alternating border")
    if all(initial[name]["observed_rgb"] == later[name]["observed_rgb"]
           for name, _, _ in SAMPLE_POINTS):
        # Texture samples may legitimately be stable; require the border phase
        # to differ, but record whether the sampled texture itself was stable.
        sample_stable = True
    else:
        sample_stable = False
    return {
        "schema": SCHEMA,
        "result": "PASS",
        "generated_only": bool(generated_only),
        "original_ps3_assets_used": not generated_only,
        "physical_switch_verified": False,
        "source_bytes": len(blob),
        "source_sha256": source_hash,
        "source_format": "classic BGRA8 DDS",
        "source_dimensions": [256, 256],
        "native_upload_marker_verified": True,
        "real_neixium_frame_count": 2,
        "sample_filter": "linear min/mag, clamp-to-edge",
        "quad_clip_bounds": [QUAD_MIN, QUAD_MIN, QUAD_MAX, QUAD_MAX],
        "sample_tolerance_rgb": TOLERANCE,
        "alpha_policy": (
            "RGB compared from host-window screenshots; capture alpha is not "
            "authoritative. Stage340 independently checked all RGBA channels "
            "through GPU image-to-buffer readback."
        ),
        "frames_distinct_at_alternating_border": True,
        "texture_samples_stable_between_frames": sample_stable,
        "samples": {"initial": initial, "later": later},
    }


def publish_public(report_path: Path, evidence: Path, output: Path) -> dict:
    report_path, evidence, output = Path(report_path), Path(evidence), Path(output)
    report = json.loads(_regular(report_path, 256 * 1024).decode("utf-8"))
    if report.get("schema") != SCHEMA or report.get("result") != "PASS":
        raise ValueError("Stage341 aggregate schema/result mismatch")
    if report.get("generated_only") is not True or \
       report.get("original_ps3_assets_used") is not False:
        raise ValueError("Stage341 refuses to publish non-generated source evidence")
    _check_tree(evidence, True)
    source_hash = report.get("source_sha256")
    source_bytes = report.get("source_bytes")
    if not isinstance(source_hash, str) or type(source_bytes) is not int or \
       _hash_file(evidence / "source-before.sha256") != source_hash or \
       _hash_file(evidence / "source-after.sha256") != source_hash:
        raise ValueError("Stage341 public source/provenance hash mismatch")
    _valid_generated_input(evidence / "generated-input.json",
                           source_hash, source_bytes)
    if report.get("native_upload_marker_verified") is not True or \
       report.get("real_neixium_frame_count") != 2 or \
       report.get("physical_switch_verified") is not False or \
       set(report.get("samples", {})) != {"initial", "later"}:
        raise ValueError("Stage341 public evidence contract mismatch")
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise ValueError("Stage341 public output must be a fresh path")
    output.mkdir(mode=0o700)
    safe = {
        "schema": SCHEMA,
        "result": "PASS",
        "generated_only": True,
        "original_ps3_assets_used": False,
        "physical_switch_verified": False,
        "source_dimensions": report["source_dimensions"],
        "source_bytes": report["source_bytes"],
        "source_sha256": report["source_sha256"],
        "native_upload_marker_verified": True,
        "real_neixium_frame_count": 2,
        "sample_filter": report["sample_filter"],
        "quad_clip_bounds": report["quad_clip_bounds"],
        "sample_tolerance_rgb": report["sample_tolerance_rgb"],
        "alpha_policy": report["alpha_policy"],
        "frames_distinct_at_alternating_border": True,
        "texture_samples_stable_between_frames":
            report["texture_samples_stable_between_frames"],
        "samples": report["samples"],
    }
    (output / "stage341-frame-audit.json").write_text(
        json.dumps(safe, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    checksum = _hash_file(evidence / "nexium-archive.sha256")
    (output / "nexium-archive.sha256").write_text(checksum + "\n",
                                                  encoding="ascii")
    actual = {p.name for p in output.iterdir() if p.is_file() and not p.is_symlink()}
    if actual != {"stage341-frame-audit.json", "nexium-archive.sha256"}:
        raise ValueError("Stage341 public output violated strict allowlist")
    return safe


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--source-dds", type=Path, required=True)
    a.add_argument("--evidence", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--generated-only", action="store_true")
    p = sub.add_parser("publish-public")
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "audit":
            report = audit(args.source_dds, args.evidence, args.generated_only)
            if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
                raise ValueError("Stage341 report output must be fresh")
            args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                                   encoding="utf-8")
            print("STAGE341_REAL_NEIXIUM_FRAME_AUDIT_PASS")
        else:
            publish_public(args.report, args.evidence, args.output)
            print("STAGE341_PUBLIC_AGGREGATE_EXPORT_PASS")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
