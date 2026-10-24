#!/usr/bin/env python3
"""Stage340 DDS-to-GPU frame audit.

The public CI fixture is generated-only. A private owner run may point this
same gate at an owner-local original DDS, but its raw evidence and SHA-256
must stay in private storage and must never be passed to publish().
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import shutil
import struct
import sys
from pathlib import Path

from PIL import Image

SCHEMA = "foj.stage340.private_dds_gpu_frame.v1"
AGGREGATE_SCHEMA = "foj.stage340.generated_dds_gpu_aggregate.v1"
MARKER_NAME = "foj-stage340-private-dds-gpu.txt"
RECEIPT_NAME = "stage340-gpu-frame-receipt.json"
FRAMES = ("gpu-initial.png", "gpu-later.png")
PUBLIC_FILES = {"stage340-frame-proof.json", "nexium-archive.sha256"}
SOURCE_FILES = {"nexium-archive.sha256"} | {
    "bridge/" + name for name in (
        "generated-input.json", MARKER_NAME, *FRAMES, RECEIPT_NAME, "guest.log"
    )
}
ARCHIVE_RE = re.compile(rb"[0-9a-f]{64}  /tmp/nexium\\.tar\\.gz\\n")
MARKER_BYTES = (
    b"FOJ_STAGE340_PRIVATE_DDS_GPU_V1 frame=1 upload=1 sample_draw=1\\n"
)
DDS_LIMIT = 32 * 1024 * 1024
FRAME_SIZE = (1280, 720)
SAMPLE_X = (71, 213, 355, 497, 639, 781, 923, 1065, 1207)
SAMPLE_Y = (61, 143, 227, 311, 409, 493, 577, 659)


def _regular(path: Path, limit: int = 8 * 1024 * 1024) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected a regular evidence file")
    if path.stat().st_size > limit:
        raise ValueError("evidence file exceeds its bound")
    return path.read_bytes()


def _check_tree(folder: Path, allowed: set[str]) -> None:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("evidence root is invalid")
    actual = set()
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise ValueError("symlink in evidence tree")
        if path.is_file():
            actual.add(path.relative_to(folder).as_posix())
        elif not path.is_dir():
            raise ValueError("special file in evidence tree")
    if actual != allowed:
        raise ValueError("evidence tree differs from strict allowlist")


def make_synthetic_dds() -> bytes:
    """A deterministic 64x64 BGRA32 DDS fixture; contains no game pixels."""
    width = height = 64
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)
    struct.pack_into("<I", header, 8, 0x1007)
    struct.pack_into("<I", header, 12, height)
    struct.pack_into("<I", header, 16, width)
    struct.pack_into("<I", header, 20, 0)
    struct.pack_into("<I", header, 24, 0)
    struct.pack_into("<I", header, 28, 0)
    struct.pack_into("<I", header, 76, 32)
    struct.pack_into("<I", header, 80, 0x41)
    struct.pack_into("<I", header, 84, 0)
    struct.pack_into("<I", header, 88, 32)
    struct.pack_into("<I", header, 92, 0x00FF0000)
    struct.pack_into("<I", header, 96, 0x0000FF00)
    struct.pack_into("<I", header, 100, 0x000000FF)
    struct.pack_into("<I", header, 104, 0xFF000000)
    struct.pack_into("<I", header, 108, 0x1002)
    payload = bytearray()
    for y in range(height):
        for x in range(width):
            red = (x * 4) & 255
            green = (y * 4) & 255
            blue = ((x * 13) ^ (y * 7)) & 255
            payload.extend((blue, green, red, 255))
    return bytes(header + payload)


def _dds_meta(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("input is not a classic DDS")
    if struct.unpack_from("<I", data, 4)[0] != 124:
        raise ValueError("invalid DDS header size")
    width = struct.unpack_from("<I", data, 16)[0]
    height = struct.unpack_from("<I", data, 12)[0]
    flags = struct.unpack_from("<I", data, 80)[0]
    fourcc = struct.unpack_from("<I", data, 84)[0]
    bits = struct.unpack_from("<I", data, 88)[0]
    if flags == 0x41 and bits == 32:
        fmt = "BGRA32"
    elif flags == 0x40 and bits == 24:
        fmt = "BGR24"
    elif flags == 0x4 and fourcc == 0x31545844:
        fmt = "BC1"
    elif flags == 0x4 and fourcc == 0x33545844:
        fmt = "BC2"
    else:
        raise ValueError("unsupported DDS pixel format")
    if not 0 < width <= 2048 or not 0 < height <= 2048 or width * height > 2048 * 2048:
        raise ValueError("DDS dimensions outside supported bounds")
    return {"width": width, "height": height, "format": fmt, "bytes": len(data)}


def _decode_rgba(data: bytes):
    if len(data) > DDS_LIMIT:
        raise ValueError("DDS source exceeds bounded size")
    meta = _dds_meta(data)
    with Image.open(io.BytesIO(data)) as source:
        if source.format != "DDS" or source.size != (meta["width"], meta["height"]):
            raise ValueError("DDS decoder disagrees with checked header")
        source.load()
        rgba = source.convert("RGBA")
        pixels = rgba.tobytes()
    if len(pixels) != meta["width"] * meta["height"] * 4:
        raise ValueError("decoded RGBA size mismatch")
    return meta, pixels


def _sample_orientation(frame_data: bytes, width: int, height: int, rgba: bytes,
                        flip_y: bool) -> dict:
    with Image.open(io.BytesIO(frame_data)) as frame:
        actual = frame.convert("RGB")
    if actual.size != FRAME_SIZE:
        raise ValueError("NeXium frame dimensions are not 1280x720")
    src = Image.frombytes("RGBA", (width, height), rgba)
    src_px = src.load()
    act_px = actual.load()
    matched = tested = 0
    for sy in SAMPLE_Y:
        for sx in SAMPLE_X:
            tx = min(width - 1, int((sx + 0.5) * width / FRAME_SIZE[0]))
            ty = min(height - 1, int((sy + 0.5) * height / FRAME_SIZE[1]))
            if flip_y:
                ty = height - 1 - ty
            expected = src_px[tx, ty]
            if expected[3] < 128:
                continue
            got = act_px[sx, sy]
            best_error = 256
            # The neighborhood allows only a one-source-texel raster edge
            # ambiguity; the DDS upload itself remains nearest-filtered.
            for yy in range(max(0, ty - 1), min(height, ty + 2)):
                for xx in range(max(0, tx - 1), min(width, tx + 2)):
                    candidate = src_px[xx, yy]
                    if candidate[3] < 128:
                        continue
                    error = max(abs(got[c] - candidate[c]) for c in range(3))
                    best_error = min(best_error, error)
            tested += 1
            if best_error <= 14:
                matched += 1
    needed = max(20, math.ceil(tested * 0.78))
    return {
        "orientation": "vertical-flip" if flip_y else "top-left",
        "matched_samples": matched,
        "tested_samples": tested,
        "pass": tested >= 20 and matched >= needed,
    }


def audit_frame(frame_path: Path, dds_data: bytes) -> dict:
    frame_data = _regular(frame_path, 24 * 1024 * 1024)
    meta, rgba = _decode_rgba(dds_data)
    direct = _sample_orientation(frame_data, meta["width"], meta["height"], rgba, False)
    flipped = _sample_orientation(frame_data, meta["width"], meta["height"], rgba, True)
    if direct["pass"]:
        return direct
    if flipped["pass"]:
        return flipped
    raise ValueError("frame pixels do not match the decoded DDS")


def _generated_input(data: bytes) -> dict:
    meta = _dds_meta(data)
    return {
        "schema": SCHEMA,
        "generated_only": True,
        "original_ps3_assets_used": False,
        "user_dds_files_read": False,
        "fixture_sha256": hashlib.sha256(data).hexdigest(),
        "fixture_bytes": len(data),
        "width": meta["width"],
        "height": meta["height"],
        "format": meta["format"],
        "pattern": "generated-coordinate-gradient-v1",
    }


def prepare(sd_root: Path, evidence: Path) -> dict:
    sd_root, evidence = Path(sd_root), Path(evidence)
    if sd_root.is_symlink() or not sd_root.is_dir():
        raise ValueError("SD root must already exist and not be a symlink")
    gpu = sd_root / "switch" / "foj" / "gpu"
    if gpu.is_symlink() or not gpu.is_dir():
        raise ValueError("GPU SD directory must already exist")
    for shader in ("foj_actor.vert.dksh", "foj_triangle.frag.dksh"):
        if not (gpu / shader).is_file() or (gpu / shader).is_symlink():
            raise ValueError("required generated shader missing")
    dds_path = gpu / "material0.dds"
    if dds_path.exists() or dds_path.is_symlink():
        raise ValueError("refusing to overwrite an existing DDS")
    if evidence.is_symlink() or not evidence.is_dir():
        raise ValueError("evidence directory must already exist")
    input_path = evidence / "generated-input.json"
    if input_path.exists() or input_path.is_symlink():
        raise ValueError("refusing to overwrite generated input metadata")
    data = make_synthetic_dds()
    with dds_path.open("xb") as output:
        output.write(data)
    input_path.write_text(
        json.dumps(_generated_input(data), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"schema": SCHEMA, "generated_only": True, "fixture_ready": True}


def audit(source_dds: Path, evidence: Path, expected_sha256: str | None = None,
          original_ps3: bool = False) -> dict:
    source_dds, evidence = Path(source_dds), Path(evidence)
    dds_data = _regular(source_dds, DDS_LIMIT)
    meta, _ = _decode_rgba(dds_data)
    source_hash = hashlib.sha256(dds_data).hexdigest()
    if expected_sha256 is not None and source_hash != expected_sha256:
        raise ValueError("source DDS changed during the GPU run")
    marker = _regular(evidence / MARKER_NAME, 1024)
    if marker != MARKER_BYTES:
        raise ValueError("native upload/sample receipt missing or malformed")
    generated_path = evidence / "generated-input.json"
    generated = False
    if generated_path.exists() or generated_path.is_symlink():
        saved = json.loads(_regular(generated_path, 65536))
        if saved != _generated_input(dds_data):
            raise ValueError("generated-only source identity mismatch")
        generated = True
    if generated and original_ps3:
        raise ValueError("generated fixture cannot be marked as original")
    frame_results = [audit_frame(evidence / name, dds_data) for name in FRAMES]
    orientations = {result["orientation"] for result in frame_results}
    if orientations != {"top-left"}:
        raise ValueError("GPU texture UV orientation is not top-left")
    if any(not result["pass"] for result in frame_results):
        raise ValueError("GPU frame pixel oracle failed")
    receipt = {
        "schema": SCHEMA,
        "source_kind": "generated-only" if generated else (
            "owner-original-ps3-dds" if original_ps3 else "owner-private-dds"
        ),
        "source_sha256": source_hash,
        "source_bytes": len(dds_data),
        "source_width": meta["width"],
        "source_height": meta["height"],
        "source_format": meta["format"],
        "frame_count": 2,
        "frame_pixel_oracle_passed": True,
        "uv_orientation": "top-left",
        "frame_samples": [
            {k: item[k] for k in ("matched_samples", "tested_samples", "orientation")}
            for item in frame_results
        ],
        "frames_identical": _frames_identical(
            evidence / FRAMES[0], evidence / FRAMES[1]
        ),
        "generated_only": generated,
        "original_ps3_assets_used": bool(original_ps3),
        "user_dds_files_read": not generated,
        "physical_switch_verified": False,
        "raw_pixels_saved": False,
    }
    receipt_path = evidence / RECEIPT_NAME
    if receipt_path.exists() or receipt_path.is_symlink():
        raise ValueError("refusing to overwrite a prior receipt")
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    return receipt


def _frames_identical(a: Path, b: Path) -> bool:
    return _regular(a, 24 * 1024 * 1024) == _regular(b, 24 * 1024 * 1024)


def verify_and_aggregate(source: Path) -> dict:
    source = Path(source)
    _check_tree(source, SOURCE_FILES)
    bridge = source / "bridge"
    fixture = make_synthetic_dds()
    expected_input = _generated_input(fixture)
    saved_input = json.loads(_regular(bridge / "generated-input.json", 65536))
    if saved_input != expected_input:
        raise ValueError("public evidence does not describe the fixed generated fixture")
    marker = _regular(bridge / MARKER_NAME, 1024)
    if marker != MARKER_BYTES:
        raise ValueError("native GPU receipt is missing")
    receipt = json.loads(_regular(bridge / RECEIPT_NAME, 65536))
    if (receipt.get("schema") != SCHEMA or
            receipt.get("source_kind") != "generated-only" or
            receipt.get("source_sha256") != expected_input["fixture_sha256"] or
            receipt.get("generated_only") is not True or
            receipt.get("original_ps3_assets_used") is not False or
            receipt.get("user_dds_files_read") is not False or
            receipt.get("physical_switch_verified") is not False or
            receipt.get("frame_count") != 2 or
            receipt.get("frame_pixel_oracle_passed") is not True or
            receipt.get("uv_orientation") != "top-left"):
        raise ValueError("generated-only GPU receipt violates source/proof contract")
    frame_results = [audit_frame(bridge / name, fixture) for name in FRAMES]
    if any(result["orientation"] != "top-left" for result in frame_results):
        raise ValueError("fresh screenshot audit detected a texture orientation mismatch")
    checksum = _regular(source / "nexium-archive.sha256", 256)
    if not ARCHIVE_RE.fullmatch(checksum):
        raise ValueError("NeXium binary identity checksum is missing")
    log = bridge / "guest.log"
    if log.is_symlink() or not log.is_file() or log.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("bounded guest log missing")
    return {
        "schema": AGGREGATE_SCHEMA,
        "native_nro": "foj-deko3d-stage340-private-dds.nro",
        "texture_path": "Stage332/339 DDS decode -> Stage335 staging plan -> Stage336 native upload -> GPU sample",
        "source_texture_kind": "generated-only-fixture",
        "generated_only": True,
        "gpu_texture_sampling_verified": True,
        "real_neixium_frames_verified": 2,
        "independent_cpu_dds_pixel_oracle": True,
        "sampled_pixels_per_frame_min": min(x["matched_samples"] for x in frame_results),
        "uv_orientation": "top-left",
        "screenshots_published": False,
        "guest_log_published": False,
        "original_ps3_assets_used": False,
        "user_dds_files_read": False,
        "physical_switch_verified": False,
    }


def publish(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    proof = verify_and_aggregate(source)
    if output.exists() or output.is_symlink() or not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("refusing to overwrite public aggregate output")
    output.mkdir(mode=0o700)
    try:
        (output / "stage340-frame-proof.json").write_text(
            json.dumps(proof, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        with (output / "nexium-archive.sha256").open("xb") as target:
            target.write(_regular(source / "nexium-archive.sha256", 256))
        _check_tree(output, PUBLIC_FILES)
        if json.loads(_regular(output / "stage340-frame-proof.json", 65536)) != proof:
            raise ValueError("public aggregate changed during export")
    except BaseException:
        shutil.rmtree(output)
        raise
    return proof


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--sd-root", required=True, type=Path)
    p_prepare.add_argument("--evidence", required=True, type=Path)
    p_frame = sub.add_parser("frame")
    p_frame.add_argument("--image", required=True, type=Path)
    p_frame.add_argument("--source-dds", required=True, type=Path)
    p_audit = sub.add_parser("audit")
    p_audit.add_argument("--source-dds", required=True, type=Path)
    p_audit.add_argument("--evidence", required=True, type=Path)
    p_audit.add_argument("--expected-sha256")
    p_audit.add_argument("--original-ps3", action="store_true")
    p_publish = sub.add_parser("publish")
    p_publish.add_argument("--source", required=True, type=Path)
    p_publish.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.sd_root, args.evidence)
            print("STAGE340_GENERATED_DDS_INPUT_READY")
        elif args.command == "frame":
            data = _regular(args.source_dds, DDS_LIMIT)
            results = audit_frame(args.image, data)
            if not results["pass"]:
                raise ValueError("frame audit failed")
            print("STAGE340_DDS_FRAME_PIXEL_ORACLE_PASS")
        elif args.command == "audit":
            result = audit(args.source_dds, args.evidence,
                           args.expected_sha256, args.original_ps3)
            print("STAGE340_GENERATED_DDS_GPU_FRAME_AUDIT_PASS" if result["generated_only"]
                  else "STAGE340_OWNER_PRIVATE_DDS_GPU_FRAME_AUDIT_PASS")
        else:
            publish(args.source, args.output)
            print("STAGE340_GENERATED_DDS_SAFE_AGGREGATE_PASS")
    except (OSError, TypeError, KeyError, ValueError, json.JSONDecodeError):
        print("Stage340 DDS evidence refused.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
