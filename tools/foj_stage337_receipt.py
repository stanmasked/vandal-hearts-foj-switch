"""Generated-only owner-safe proof for the Stage337 GPU copy roundtrip.

Only read the exact guest-generated success record; never publish guest logs.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

MARKER_NAME = "foj-stage337-native-roundtrip.txt"
MARKER = b"STAGE337_DEKO3D_GPU_ROUNDTRIP_V1 w=74 h=81 pixels=5994 diff=0\n"


def check(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != len(MARKER):
        raise ValueError("Stage337 receipt missing or modified")
    if path.read_bytes() != MARKER:
        raise ValueError("Stage337 receipt is not an exact GPU witness")


def publish(input_path: Path, directory: Path) -> None:
    check(input_path)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Stage337 output directory missing")
    final = directory / "stage337-gpu-readback.json"
    if final.exists() or final.is_symlink():
        raise ValueError("Stage337 refuses previously stored reports")
    final.write_text(json.dumps({
        "schema": "foj.stage337.native_gpu_roundtrip.v1",
        "width": 74, "height": 81, "rgba_pixels": 5994,
        "different_pixels": 0, "mode": "generated_only_real_gpu_image_copy_readback",
        "original_ps3_assets_included": False,
        "physical_switch_verified": False,
        "framebuffer_verified": False,
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("check", "publish"))
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "check":
        check(args.receipt)
    else:
        if args.output is None:
            parser.error("--output is required")
        publish(args.receipt, args.output)


if __name__ == "__main__":
    main()
