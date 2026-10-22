#!/usr/bin/env python3
"""Stage329 generated-only NeXium audit for a real deko3d corner-patch draw."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
import shutil
import sys
from pathlib import Path
from PIL import Image, ImageChops

SCHEMA = "foj.stage329.generated_corner_patch_neixium.v1"
MARKER = "native-stage329-corner-patch-upload.txt"
RECEIPT = "stage329-corner-patch-gpu-receipt.json"
FRAMES = ("gpu-initial.png", "gpu-later.png")
MARKER_BYTES = (
    b"FOJ_NATIVE_STAGE329_CORNER_PATCH_UPLOAD_V1 junction=2,2 "
    b"tile=16x16 bytes=1024 fnv1a64=d5565bfb7360b325 "
    b"midpoint=128,128,128,255 vertices=3 sections=1 texture=1\n"
)
SHADERS = ("foj_actor.vert.dksh", "foj_triangle.frag.dksh")
SOURCE_FILES = {"nexium-archive.sha256"} | {
    "bridge/" + name for name in (
        "generated-input.json", MARKER, *FRAMES, RECEIPT, "guest.log"
    )
}
PUBLIC_FILES = SOURCE_FILES - {"bridge/guest.log"}
CORNER_COLORS = {
    "nw": (255, 0, 0),
    "ne": (0, 255, 0),
    "sw": (0, 0, 255),
    "se": (255, 255, 255),
}


def _regular(path: Path, limit: int = 65536) -> bytes:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage329 expected a regular evidence file")
    if path.stat().st_size > limit:
        raise ValueError("Stage329 evidence file exceeds its bound")
    return path.read_bytes()


def _write_new(folder: Path, name: str, payload: dict) -> None:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage329 evidence folder must already exist")
    path = folder / name
    if path.exists() or path.is_symlink():
        raise ValueError("Stage329 refuses to overwrite evidence")
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def _check_tree(folder: Path, allowed: set[str]) -> None:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage329 evidence root invalid")
    actual = set()
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise ValueError("Stage329 refuses symlinks in evidence")
        if path.is_file():
            actual.add(path.relative_to(folder).as_posix())
        elif not path.is_dir():
            raise ValueError("Stage329 refuses special files")
    if actual != allowed:
        raise ValueError("Stage329 evidence tree differs from strict allowlist")


def _origin(shader_dir: Path) -> dict:
    hashes = {}
    for name in SHADERS:
        data = _regular(Path(shader_dir) / name, 1024 * 1024)
        if not data:
            raise ValueError("Stage329 generated shader is empty")
        hashes[name] = hashlib.sha256(data).hexdigest()
    return {
        "schema": SCHEMA,
        "generated_only": True,
        "generated_page_order": ["northwest", "northeast", "southwest", "southeast"],
        "generated_page_rgba": [
            [255, 0, 0, 255], [0, 255, 0, 255],
            [0, 0, 255, 255], [255, 255, 255, 255],
        ],
        "junction_page_xy": [2, 2],
        "expected_tile": {
            "width": 16, "height": 16, "bytes": 1024,
            "fnv1a64": "d5565bfb7360b325",
            "midpoint_rgba": [128, 128, 128, 255],
        },
        "expected_stream": {
            "source_triangles": 1, "vertices": 3, "sections": 1,
            "tile_fragments": 1, "remainder_fragments": 0,
            "tile_texture_index": 1,
        },
        "shader_sha256": hashes,
        "original_ps3_assets_used": False,
        "user_dds_files_read": False,
        "physical_switch_verified": False,
    }


def _valid_origin(value: dict) -> bool:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        return False
    fixed = {
        "generated_only": True,
        "generated_page_order": ["northwest", "northeast", "southwest", "southeast"],
        "generated_page_rgba": [
            [255, 0, 0, 255], [0, 255, 0, 255],
            [0, 0, 255, 255], [255, 255, 255, 255],
        ],
        "junction_page_xy": [2, 2],
        "expected_tile": {
            "width": 16, "height": 16, "bytes": 1024,
            "fnv1a64": "d5565bfb7360b325",
            "midpoint_rgba": [128, 128, 128, 255],
        },
        "expected_stream": {
            "source_triangles": 1, "vertices": 3, "sections": 1,
            "tile_fragments": 1, "remainder_fragments": 0,
            "tile_texture_index": 1,
        },
        "original_ps3_assets_used": False,
        "user_dds_files_read": False,
        "physical_switch_verified": False,
    }
    if any(value.get(key) != expected for key, expected in fixed.items()):
        return False
    hashes = value.get("shader_sha256")
    return (
        isinstance(hashes, dict) and set(hashes) == set(SHADERS) and
        all(isinstance(hashes[name], str) and
            re.fullmatch(r"[0-9a-f]{64}", hashes[name]) for name in SHADERS)
    )


def prepare(sd_root: Path, evidence: Path) -> dict:
    sd_root, evidence = Path(sd_root), Path(evidence)
    gpu_dir = sd_root / "switch" / "foj" / "gpu"
    if (sd_root.is_symlink() or not sd_root.is_dir() or
            gpu_dir.is_symlink() or not gpu_dir.is_dir() or
            evidence.exists() or evidence.is_symlink() or
            not evidence.parent.is_dir() or evidence.parent.is_symlink()):
        raise ValueError("Stage329 requires a fresh evidence folder and SD shader directory")
    entries = list(gpu_dir.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in entries) or \
       {p.name for p in entries} != set(SHADERS):
        raise ValueError("Stage329 SD directory must contain only the two generated DKSH files")
    marker_path = gpu_dir / ("foj-" + MARKER)
    if marker_path.exists() or marker_path.is_symlink():
        raise ValueError("Stage329 refuses a stale native upload marker")
    evidence.mkdir(mode=0o700)
    result = _origin(gpu_dir)
    _write_new(evidence, "generated-input.json", result)
    return result


def _close_rgb(a, b, tolerance: int) -> bool:
    return all(abs(int(a[i]) - int(b[i])) <= tolerance for i in range(3))


def _frame(path: Path) -> dict:
    data = _regular(path, 12 * 1024 * 1024)
    with Image.open(io.BytesIO(data)) as source:
        image = source.convert("RGB")
    if image.size != (1280, 720):
        raise ValueError("Stage329 screenshot is not a 1280x720 NeXium frame")
    pixels = image.load()
    candidates = []
    for y in range(340, 381, 2):
        for x in range(620, 661, 2):
            if not _close_rgb(pixels[x, y], (128, 128, 128), 24):
                continue
            count = sum(
                _close_rgb(pixels[xx, yy], (128, 128, 128), 30)
                for xx in range(x - 1, x + 2)
                for yy in range(y - 1, y + 2)
            )
            if count >= 5:
                candidates.append((abs(x - 640) + abs(y - 360), x, y, count))
    if not candidates:
        raise ValueError("Stage329 four-page GPU midpoint not found")
    _, cx, cy, center_count = min(candidates)
    center = tuple(pixels[cx, cy])
    if not _close_rgb(center, (128, 128, 128), 26):
        raise ValueError("Stage329 center is not the expected four-color average")

    left, right = tuple(pixels[cx - 20, cy]), tuple(pixels[cx + 20, cy])
    top, bottom = tuple(pixels[cx, cy - 20]), tuple(pixels[cx, cy + 20])
    if right[1] - left[1] < 28:
        raise ValueError("Stage329 horizontal green interpolation is absent")
    if bottom[2] - top[2] < 28:
        raise ValueError("Stage329 vertical blue interpolation is absent")

    samples = {
        "nw": tuple(pixels[cx - 20, cy - 20]),
        "ne": tuple(pixels[cx + 20, cy - 20]),
        "sw": tuple(pixels[cx - 20, cy + 20]),
        "se": tuple(pixels[cx + 20, cy + 20]),
    }
    if not (samples["nw"][0] > samples["nw"][1] + 18 and
            samples["nw"][0] > samples["nw"][2] + 18):
        raise ValueError("Stage329 northwest red contribution is absent")
    if not (samples["ne"][1] > samples["ne"][0] + 18 and
            samples["ne"][1] > samples["ne"][2] + 18):
        raise ValueError("Stage329 northeast green contribution is absent")
    if not (samples["sw"][2] > samples["sw"][0] + 18 and
            samples["sw"][2] > samples["sw"][1] + 18):
        raise ValueError("Stage329 southwest blue contribution is absent")
    if min(samples["se"]) < 105:
        raise ValueError("Stage329 southeast white contribution is absent")

    outside = (tuple(pixels[max(0, cx - 80), cy]),
               tuple(pixels[min(1279, cx + 80), cy]))
    if any(_close_rgb(color, (128, 128, 128), 10) for color in outside):
        raise ValueError("Stage329 patch footprint does not end outside its triangle")
    return {
        "center_x": cx, "center_y": cy,
        "midpoint_rgb": list(center),
        "midpoint_cluster_pixels": center_count,
        "horizontal_green_delta": right[1] - left[1],
        "vertical_blue_delta": bottom[2] - top[2],
        "quadrant_samples": {key: list(value) for key, value in samples.items()},
        "outside_triangle_samples": [list(value) for value in outside],
    }


def audit(folder: Path) -> dict:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage329 evidence folder invalid")
    origin = json.loads(_regular(folder / "generated-input.json"))
    if not _valid_origin(origin):
        raise ValueError("Stage329 synthetic input provenance mismatch")
    if _regular(folder / MARKER) != MARKER_BYTES:
        raise ValueError("Stage329 native upload receipt mismatch")
    frames = {name: _frame(folder / name) for name in FRAMES}
    with Image.open(io.BytesIO(_regular(folder / FRAMES[0], 12 * 1024 * 1024))) as first, \
         Image.open(io.BytesIO(_regular(folder / FRAMES[1], 12 * 1024 * 1024))) as later:
        a, b = first.convert("RGB"), later.convert("RGB")
    if ImageChops.difference(a, b).getbbox() is None:
        raise ValueError("Stage329 captured duplicate GPU frames")
    if (abs(frames[FRAMES[0]]["center_x"] - frames[FRAMES[1]]["center_x"]) > 2 or
            abs(frames[FRAMES[0]]["center_y"] - frames[FRAMES[1]]["center_y"]) > 2):
        raise ValueError("Stage329 GPU patch center drifted between captures")
    return {
        "schema": "foj.stage329.real_neixium_corner_patch_gpu.v1",
        "generated_only": True,
        "native_upload_receipt_verified": True,
        "real_neixium_frames_verified": 2,
        "gpu_tile_midpoint_verified": True,
        "horizontal_and_vertical_linear_interpolation_verified": True,
        "four_quadrant_contributions_verified": True,
        "frames": frames,
        "original_ps3_assets_used": False,
        "user_dds_files_read": False,
        "physical_switch_verified": False,
    }


def publish(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    if (output.exists() or output.is_symlink() or
            not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage329 public output must be a new directory")
    _check_tree(source, SOURCE_FILES)
    checked = audit(source / "bridge")
    saved = json.loads(_regular(source / "bridge" / RECEIPT))
    if checked != saved:
        raise ValueError("Stage329 saved receipt differs from fresh screenshot audit")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular(source / "nexium-archive.sha256")):
        raise ValueError("Stage329 NeXium archive checksum malformed")
    output.mkdir(mode=0o700)
    try:
        (output / "bridge").mkdir(mode=0o700)
        for relative in sorted(PUBLIC_FILES):
            limit = 12 * 1024 * 1024 if relative.endswith(".png") else 65536
            data = _regular(source / relative, limit)
            with (output / relative).open("xb") as handle:
                handle.write(data)
        _check_tree(output, PUBLIC_FILES)
        if audit(output / "bridge") != checked:
            raise ValueError("Stage329 public export fails independent re-audit")
        for relative in PUBLIC_FILES:
            limit = 12 * 1024 * 1024 if relative.endswith(".png") else 65536
            if _regular(source / relative, limit) != _regular(output / relative, limit):
                raise ValueError("Stage329 public export changed source bytes")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema": "foj.stage329.public_generated_only_gpu_evidence.v1",
        "public_files": len(PUBLIC_FILES),
        "real_neixium_frames": 2,
        "guest_log_uploaded": False,
        "original_ps3_assets_uploaded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    p = modes.add_parser("prepare")
    p.add_argument("--sd-root", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    f = modes.add_parser("frame")
    f.add_argument("--image", type=Path, required=True)
    a = modes.add_parser("audit")
    a.add_argument("--evidence", type=Path, required=True)
    q = modes.add_parser("publish")
    q.add_argument("--source", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            result = prepare(args.sd_root, args.evidence)
        elif args.mode == "frame":
            result = _frame(args.image)
        elif args.mode == "audit":
            result = audit(args.evidence)
            _write_new(args.evidence, RECEIPT, result)
        else:
            result = publish(args.source, args.output)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        print("Stage329 independent corner-patch GPU evidence refused.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
