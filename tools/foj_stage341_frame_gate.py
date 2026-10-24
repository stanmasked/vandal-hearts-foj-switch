#!/usr/bin/env python3
"""Stage341 source-to-frame audit; public mode accepts generated DDS only."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import time
from PIL import Image, ImageChops

SCHEMA = "foj.stage341.private_dds_shader_frame.v1"
MARKER_NAME = "foj-stage341-texture-sample.txt"
MARKER = (
    b"FOJ_STAGE341_PRIVATE_DDS_TEXTURE_SAMPLE_V1 width=256 height=256 "
    b"quad=80pct uv=top-left-00 nearest=1 frames-presented=2\n"
)
WIDTH = HEIGHT = 256
FRAME_WIDTH, FRAME_HEIGHT = 1280, 720
DDS_BYTES = 128 + WIDTH * HEIGHT * 4
SAMPLE_X = (256, 384, 640, 896, 1024)
SAMPLE_Y = (144, 288, 360, 432, 576)
CHANNEL_TOLERANCE = 8
MAX_BAD_CHANNELS = 0
EVIDENCE_FILES = {
    "generated-source.json", "nexium-archive.sha256", "guest.log",
    "gpu-initial.png", "gpu-later.png",
}
PRIVATE_EVIDENCE_FILES = {
    "nexium-runtime.sha256", "guest.log", "gpu-initial.png", "gpu-later.png",
}


def _regular(path: Path, limit: int) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage341 expected a regular file")
    if path.stat().st_size > limit:
        raise ValueError("Stage341 file exceeds its bound")
    return path.read_bytes()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_bgra8_dds(blob: bytes) -> bytes:
    """Strict independent BGRA8 base-mip decoder for the selected DDS profile."""
    if len(blob) != DDS_BYTES or blob[:4] != b"DDS ":
        raise ValueError("Stage341 source is not the exact bounded BGRA8 DDS envelope")
    if struct.unpack_from("<I", blob, 4)[0] != 124:
        raise ValueError("Stage341 DDS header size mismatch")
    flags = struct.unpack_from("<I", blob, 8)[0]
    height, width, pitch = struct.unpack_from("<III", blob, 12)
    mip_count = struct.unpack_from("<I", blob, 28)[0]
    pf_size, pf_flags, fourcc, bits = struct.unpack_from("<IIII", blob, 76)
    masks = struct.unpack_from("<IIII", blob, 92)
    caps = struct.unpack_from("<I", blob, 108)[0]
    canonical = flags == 0x100F and pitch == WIDTH * 4 and caps == 0x1000
    owner_profile = flags == 0x1007 and pitch == 0 and caps == 0x1002
    if (width, height) != (WIDTH, HEIGHT) or mip_count not in (0, 1):
        raise ValueError("Stage341 DDS dimensions or mip count unsupported")
    if (pf_size, pf_flags, fourcc, bits, masks) != (
        32, 0x41, 0, 32,
        (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000),
    ):
        raise ValueError("Stage341 DDS pixel format is not BGRA8")
    if not (canonical or owner_profile):
        raise ValueError("Stage341 DDS header profile unsupported")
    if any(struct.unpack_from("<I", blob, p)[0] for p in (112, 116, 120, 124)):
        raise ValueError("Stage341 DDS reserved fields must be zero")
    payload = blob[128:]
    rgba = bytearray(len(payload))
    for offset in range(0, len(payload), 4):
        rgba[offset:offset + 4] = bytes((
            payload[offset + 2], payload[offset + 1],
            payload[offset], payload[offset + 3],
        ))
    return bytes(rgba)


def _marker(sd_root: Path) -> Path:
    path = Path(sd_root) / "switch" / "foj" / "gpu" / MARKER_NAME
    if _regular(path, 256) != MARKER:
        raise ValueError("Stage341 native post-present receipt mismatch")
    return path


def _sample_uv(x: int, y: int) -> tuple[float, float]:
    # Pixel centers, matching the clip-space quad bounded to NDC +/-0.8.
    return (
        ((x + 0.5) / FRAME_WIDTH - 0.1) / 0.8,
        ((y + 0.5) / FRAME_HEIGHT - 0.1) / 0.8,
    )


def _frame_audit(path: Path, rgba: bytes, marker_mtime_ns: int) -> dict:
    path = Path(path)
    blob = _regular(path, 12 * 1024 * 1024)
    if path.stat().st_mtime_ns < marker_mtime_ns:
        raise ValueError("Stage341 framebuffer capture predates the guest receipt")
    with Image.open(io.BytesIO(blob)) as source:
        image = source.convert("RGB")
    if image.size != (FRAME_WIDTH, FRAME_HEIGHT):
        raise ValueError("Stage341 capture is not a 1280x720 NeXium client frame")
    pixels = image.load()
    comparisons = []
    bad_channels = 0
    max_error = 0
    for y in SAMPLE_Y:
        for x in SAMPLE_X:
            u, v = _sample_uv(x, y)
            tx = min(WIDTH - 1, max(0, int(u * WIDTH)))
            ty = min(HEIGHT - 1, max(0, int(v * HEIGHT)))
            source_offset = (ty * WIDTH + tx) * 4
            expected = tuple(rgba[source_offset:source_offset + 3])
            observed = tuple(pixels[x, y])
            errors = tuple(abs(observed[i] - expected[i]) for i in range(3))
            bad_channels += sum(error > CHANNEL_TOLERANCE for error in errors)
            max_error = max(max_error, *errors)
            comparisons.append((x, y, tx, ty, expected, observed, errors))
    if bad_channels > MAX_BAD_CHANNELS:
        raise ValueError(
            f"Stage341 framebuffer differs from CPU reference: "
            f"{bad_channels} RGB channels exceed tolerance {CHANNEL_TOLERANCE}"
        )
    return {
        "capture_sha256": _sha(blob),
        "sample_count": len(comparisons),
        "bad_channels": bad_channels,
        "max_rgb_channel_error": max_error,
        "tolerance": CHANNEL_TOLERANCE,
        "alpha_policy": "ignored: desktop window capture does not preserve framebuffer alpha",
        "samples_private": [
            {
                "frame_xy": [x, y], "texture_xy": [tx, ty],
                "expected_rgb": list(expected), "observed_rgb": list(observed),
                "absolute_rgb_error": list(errors),
            }
            for x, y, tx, ty, expected, observed, errors in comparisons
        ],
    }


def audit_frames(dds_path: Path, sd_root: Path, evidence: Path,
                 require_generated_metadata: bool = False) -> dict:
    dds_path, sd_root, evidence = Path(dds_path), Path(sd_root), Path(evidence)
    if evidence.is_symlink() or not evidence.is_dir():
        raise ValueError("Stage341 evidence directory must be an existing regular directory")
    actual = set()
    for item in evidence.iterdir():
        if item.is_symlink() or not item.is_file():
            raise ValueError("Stage341 evidence directory may contain regular files only")
        actual.add(item.name)
    expected_evidence = EVIDENCE_FILES if require_generated_metadata else PRIVATE_EVIDENCE_FILES
    if actual != expected_evidence:
        raise ValueError("Stage341 evidence directory differs from strict allowlist")
    source = _regular(dds_path, DDS_BYTES)
    rgba = decode_bgra8_dds(source)
    marker = _marker(sd_root)
    marker_time = marker.stat().st_mtime_ns
    first_path, later_path = evidence / "gpu-initial.png", evidence / "gpu-later.png"
    first = _frame_audit(first_path, rgba, marker_time)
    later = _frame_audit(later_path, rgba, marker_time)
    with Image.open(io.BytesIO(_regular(first_path, 12 * 1024 * 1024))) as a, \
         Image.open(io.BytesIO(_regular(later_path, 12 * 1024 * 1024))) as b:
        first_rgb, later_rgb = a.convert("RGB"), b.convert("RGB")
    if ImageChops.difference(first_rgb, later_rgb).getbbox() is None:
        raise ValueError("Stage341 duplicate framebuffer pixels rejected")
    if first["bad_channels"] or later["bad_channels"]:
        raise ValueError("Stage341 frame/reference comparison failed")
    if require_generated_metadata:
        metadata = json.loads(_regular(evidence / "generated-source.json", 4096))
        if (
            metadata.get("schema") != "foj.stage340.generated_bgra8_dds_fixture.v1"
            or metadata.get("generated_only") is not True
            or metadata.get("original_ps3_assets_used") is not False
            or metadata.get("physical_switch_verified") is not False
            or metadata.get("sha256") != _sha(source)
            or metadata.get("dds_file_bytes") != DDS_BYTES
            or metadata.get("width") != WIDTH
            or metadata.get("height") != HEIGHT
            or metadata.get("format") != "BGRA8"
        ):
            raise ValueError("Stage341 public source provenance is not generated-only")
        # The public run is the only mode allowed to publish a source hash.
    elif (evidence / "generated-source.json").exists():
        raise ValueError("Stage341 private evidence must not be mislabeled as generated-only")
    checksum_name = "nexium-archive.sha256" if require_generated_metadata else "nexium-runtime.sha256"
    runtime_hash = _regular(evidence / checksum_name, 256).decode("ascii").strip()
    runtime_pattern = (
        r"[0-9a-f]{64}  nexium-linux-x86_64\.tar\.gz"
        if require_generated_metadata else
        r"[0-9a-f]{64}  [A-Za-z0-9._-]{1,100}"
    )
    if not re.fullmatch(runtime_pattern, runtime_hash):
        raise ValueError("Stage341 NeXium runtime checksum record malformed")
    _regular(evidence / "guest.log", 2 * 1024 * 1024)
    # Ensure there are no unrecognized guest-generated files beyond the input,
    # two shader modules, marker and fixed boot-journal slots.
    gpu = sd_root / "switch" / "foj" / "gpu"
    allowed_sd = {
        "source.dds", "foj_actor.vert.dksh", "foj_triangle.frag.dksh",
        MARKER_NAME,
    }
    for item in gpu.iterdir():
        if item.is_symlink() or not item.is_file():
            raise ValueError("Stage341 SD GPU folder contains a non-regular entry")
        if item.name not in allowed_sd and not re.fullmatch(r"foj-boot-[0-9]{2}\.txt", item.name):
            raise ValueError("Stage341 SD GPU folder contains an unexpected file")
    return {
        "schema": SCHEMA,
        "generated_only": bool(require_generated_metadata),
        "original_ps3_assets_used": False if require_generated_metadata else None,
        "native_stage336_upload_receipt_verified": True,
        "native_texture_sampled_in_neixium_frame": True,
        "independent_frames_verified": 2,
        "sample_grid": [len(SAMPLE_X), len(SAMPLE_Y)],
        "samples_per_frame": len(SAMPLE_X) * len(SAMPLE_Y),
        "channel_tolerance": CHANNEL_TOLERANCE,
        "max_bad_rgb_channels": MAX_BAD_CHANNELS,
        "frame_a": {k: v for k, v in first.items() if k != "samples_private"},
        "frame_b": {k: v for k, v in later.items() if k != "samples_private"},
        "physical_switch_verified": False,
        "full_game_fidelity_verified": False,
    }


def publish(sd_root: Path, evidence: Path, output: Path) -> dict:
    evidence, output = Path(evidence), Path(output)
    if output.is_symlink() or output.exists() or not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("Stage341 public output must be a new directory under an existing safe parent")
    source_path = Path(sd_root) / "switch" / "foj" / "gpu" / "source.dds"
    result = audit_frames(source_path, sd_root, evidence, require_generated_metadata=True)
    output.mkdir(mode=0o700)
    public = {
        "schema": result["schema"],
        "generated_only": True,
        "original_ps3_assets_used": False,
        "native_stage336_upload_receipt_verified": True,
        "native_texture_sampled_in_neixium_frame": True,
        "independent_frames_verified": 2,
        "sample_grid": result["sample_grid"],
        "samples_per_frame": result["samples_per_frame"],
        "channel_tolerance": result["channel_tolerance"],
        "max_bad_rgb_channels": result["max_bad_rgb_channels"],
        "frame_a_max_rgb_channel_error": result["frame_a"]["max_rgb_channel_error"],
        "frame_b_max_rgb_channel_error": result["frame_b"]["max_rgb_channel_error"],
        "frame_a_capture_sha256": result["frame_a"]["capture_sha256"],
        "frame_b_capture_sha256": result["frame_b"]["capture_sha256"],
        "physical_switch_verified": False,
        "full_game_fidelity_verified": False,
    }
    (output / "aggregate.json").write_text(json.dumps(public, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (output / "nexium-archive.sha256").write_bytes(_regular(evidence / "nexium-archive.sha256", 256))
    if {p.name for p in output.iterdir()} != {"aggregate.json", "nexium-archive.sha256"}:
        raise ValueError("Stage341 public artifact contains an unexpected file")
    return public


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--sd-root", type=Path, required=True)
    audit.add_argument("--evidence", type=Path, required=True)
    audit.add_argument("--generated-only", action="store_true")
    pub = sub.add_parser("publish")
    pub.add_argument("--sd-root", type=Path, required=True)
    pub.add_argument("--evidence", type=Path, required=True)
    pub.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "audit":
            result = audit_frames(
                Path(args.sd_root) / "switch" / "foj" / "gpu" / "source.dds",
                args.sd_root, args.evidence, require_generated_metadata=args.generated_only,
            )
            if args.generated_only:
                result = {
                    "schema": result["schema"],
                    "generated_only": True,
                    "original_ps3_assets_used": False,
                    "native_stage336_upload_receipt_verified": True,
                    "native_texture_sampled_in_neixium_frame": True,
                    "independent_frames_verified": 2,
                    "sample_grid": result["sample_grid"],
                    "samples_per_frame": result["samples_per_frame"],
                    "channel_tolerance": result["channel_tolerance"],
                    "max_bad_rgb_channels": result["max_bad_rgb_channels"],
                    "frame_a_max_rgb_channel_error": result["frame_a"]["max_rgb_channel_error"],
                    "frame_b_max_rgb_channel_error": result["frame_b"]["max_rgb_channel_error"],
                    "physical_switch_verified": False,
                    "full_game_fidelity_verified": False,
                }
        else:
            result = publish(args.sd_root, args.evidence, args.output)
    except (OSError, ValueError, json.JSONDecodeError, struct.error) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
