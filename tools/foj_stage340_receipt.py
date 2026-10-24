#!/usr/bin/env python3
"""Stage340 generated-only guest receipt gate; never exports DDS bytes or logs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from tools.foj_stage340_fixture import verify

SCHEMA = "foj.stage340.generated_real_gpu_dds_roundtrip.v1"
MARKER_NAME = "foj-stage340-native-dds-roundtrip.txt"
PROGRESS_NAME = "foj-stage340-progress.txt"
MARKER = (
    b"STAGE340_DEKO3D_DDS_GPU_ROUNDTRIP_V1 width=256 height=256 "
    b"pixels=65536 diff=0 channels=0\n"
)
EXPECTED_PROGRESS = tuple(range(0, 11)) + (13,)


def _regular(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage340 expected a regular guest witness")
    if not 1 <= path.stat().st_size <= limit:
        raise ValueError("Stage340 guest witness outside bounded size")
    data = path.read_bytes()
    if len(data) != path.stat().st_size:
        raise ValueError("Stage340 guest witness changed while reading")
    return data


def check_marker(path: Path) -> None:
    if _regular(Path(path), 256) != MARKER:
        raise ValueError("Stage340 exact native GPU readback receipt mismatch")


def check_progress(path: Path) -> None:
    raw = _regular(Path(path), 512)
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("Stage340 progress is not bounded ASCII") from exc
    values = []
    for line in lines:
        match = re.fullmatch(r"FOJ340P1 stage=([0-9]{2})", line)
        if not match:
            raise ValueError("Stage340 malformed progress marker")
        values.append(int(match.group(1)))
    if tuple(values) != EXPECTED_PROGRESS:
        raise ValueError("Stage340 incomplete, repeated or reordered guest progress")


def audit(sd_root: Path, evidence: Path) -> dict:
    sd_root, evidence = Path(sd_root), Path(evidence)
    if sd_root.is_symlink() or not sd_root.is_dir() or evidence.is_symlink() or not evidence.is_dir():
        raise ValueError("Stage340 guest root or evidence directory missing")
    gpu = sd_root / "switch" / "foj" / "gpu"
    source = gpu / "source.dds"
    summary = verify(source)
    check_marker(gpu / MARKER_NAME)
    check_progress(gpu / PROGRESS_NAME)
    return {
        "schema": SCHEMA,
        "generated_only": True,
        "original_ps3_assets_used": False,
        "source_fixture_sha256": summary["sha256"],
        "source_unchanged_after_guest": True,
        "source_width": 256,
        "source_height": 256,
        "source_format": "BGRA8",
        "source_file_bytes": 262272,
        "rgba_pixels_uploaded": 65536,
        "native_deko3d_upload_and_queue_wait": True,
        "native_deko3d_image_to_buffer_readback_and_fence": True,
        "different_channels": 0,
        "guest_progress_sequence_verified": True,
        "physical_switch_verified": False,
        "framebuffer_verified": False,
    }


def publish(sd_root: Path, evidence: Path, output: Path) -> dict:
    result = audit(sd_root, evidence)
    output = Path(output)
    if output.is_symlink() or output.exists() or not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("Stage340 public report must be a new file")
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("check", "publish"):
        p = sub.add_parser(name)
        p.add_argument("--sd-root", type=Path, required=True)
        p.add_argument("--evidence", type=Path, required=True)
        if name == "publish":
            p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "check":
            audit(args.sd_root, args.evidence)
        else:
            publish(args.sd_root, args.evidence, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print("STAGE340_SAFE_GPU_READBACK_RECEIPT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
