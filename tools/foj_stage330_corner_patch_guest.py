#!/usr/bin/env python3
"""Stage330 generated-only NeXium audit for a real deko3d corner-patch draw."""
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

SCHEMA = "foj.stage330.generated_mixed_partition_neixium.v1"
MARKER = "native-stage330-partition-draw-upload.txt"
RECEIPT = "stage330-mixed-partition-gpu-receipt.json"
FRAMES = ("gpu-initial.png", "gpu-later.png")
MARKER_BYTES = (
    b"FOJ_NATIVE_STAGE330_PARTITION_DRAW_UPLOAD_V1 junction=2,2 "
    b"tile=16x16 bytes=1024 fnv1a64=d5565bfb7360b325 "
    b"midpoint=128,128,128,255 vertices=9 sections=2 "
    b"source_texture=0 tile_texture=1 remainder_fragments=1 "
    b"tile_fragments=1 remainder_triangles=1 tile_triangles=2\n"
)
MARKER_PATTERN = re.compile(
    rb"FOJ_NATIVE_STAGE330_PARTITION_DRAW_UPLOAD_V1 junction=2,2 "
    rb"tile=16x16 bytes=1024 fnv1a64=d5565bfb7360b325 "
    rb"midpoint=128,128,128,255 vertices=([0-9]+) sections=2 "
    rb"source_texture=0 tile_texture=1 remainder_fragments=1 "
    rb"tile_fragments=1 remainder_triangles=([1-9][0-9]*) tile_triangles=2\n"
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
        raise ValueError("Stage330 expected a regular evidence file")
    if path.stat().st_size > limit:
        raise ValueError("Stage330 evidence file exceeds its bound")
    return path.read_bytes()


def _write_new(folder: Path, name: str, payload: dict) -> None:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage330 evidence folder must already exist")
    path = folder / name
    if path.exists() or path.is_symlink():
        raise ValueError("Stage330 refuses to overwrite evidence")
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def _check_tree(folder: Path, allowed: set[str]) -> None:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage330 evidence root invalid")
    actual = set()
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise ValueError("Stage330 refuses symlinks in evidence")
        if path.is_file():
            actual.add(path.relative_to(folder).as_posix())
        elif not path.is_dir():
            raise ValueError("Stage330 refuses special files")
    if actual != allowed:
        raise ValueError("Stage330 evidence tree differs from strict allowlist")


def _origin(shader_dir: Path) -> dict:
    hashes = {}
    for name in SHADERS:
        data = _regular(Path(shader_dir) / name, 1024 * 1024)
        if not data:
            raise ValueError("Stage330 generated shader is empty")
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
            "source_triangles": 1, "minimum_vertices": 9,
            "maximum_vertices": 57, "sections": 2,
            "tile_fragments": 1, "remainder_fragments": 1,
            "tile_triangles": 2, "source_texture_index": 0,
            "tile_texture_index": 1,
            "draw_order": ["source-remainder", "corner-tile"],
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
            "source_triangles": 1, "minimum_vertices": 9,
            "maximum_vertices": 57, "sections": 2,
            "tile_fragments": 1, "remainder_fragments": 1,
            "tile_triangles": 2, "source_texture_index": 0,
            "tile_texture_index": 1,
            "draw_order": ["source-remainder", "corner-tile"],
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
        raise ValueError("Stage330 requires a fresh evidence folder and SD shader directory")
    entries = list(gpu_dir.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in entries) or \
       {p.name for p in entries} != set(SHADERS):
        raise ValueError("Stage330 SD directory must contain only the two generated DKSH files")
    marker_path = gpu_dir / ("foj-" + MARKER)
    if marker_path.exists() or marker_path.is_symlink():
        raise ValueError("Stage330 refuses a stale native upload marker")
    evidence.mkdir(mode=0o700)
    result = _origin(gpu_dir)
    _write_new(evidence, "generated-input.json", result)
    return result


def _close_rgb(a, b, tolerance: int) -> bool:
    return all(abs(int(a[i]) - int(b[i])) <= tolerance for i in range(3))


def _valid_marker(data: bytes) -> bool:
    match = MARKER_PATTERN.fullmatch(data)
    if not match:
        return False
    vertices, remainder_triangles = (int(value) for value in match.groups())
    return 9 <= vertices <= 57 and vertices == 3 * (remainder_triangles + 2)


def _frame(path: Path) -> dict:
    data = _regular(path, 12 * 1024 * 1024)
    with Image.open(io.BytesIO(data)) as source:
        image = source.convert("RGB")
    if image.size != (1280, 720):
        raise ValueError("Stage330 screenshot is not a 1280x720 NeXium frame")
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
        raise ValueError("Stage330 four-page GPU midpoint not found")
    _, cx, cy, center_count = min(candidates)
    center = tuple(pixels[cx, cy])
    if not _close_rgb(center, (128, 128, 128), 26):
        raise ValueError("Stage330 center is not the expected four-color average")

    left, right = tuple(pixels[cx - 20, cy]), tuple(pixels[cx + 20, cy])
    top, bottom = tuple(pixels[cx, cy - 20]), tuple(pixels[cx, cy + 20])
    if left[1] > 16 or right[1] < 239:
        raise ValueError("Stage330 central tile's horizontal material transition is absent")
    if top[2] > 16 or bottom[2] < 239:
        raise ValueError("Stage330 central tile's vertical material transition is absent")

    samples = {
        "nw": tuple(pixels[cx - 20, cy - 20]),
        "ne": tuple(pixels[cx + 20, cy - 20]),
        "sw": tuple(pixels[cx - 20, cy + 20]),
        "se": tuple(pixels[cx + 20, cy + 20]),
    }
    if not (samples["nw"][0] > samples["nw"][1] + 18 and
            samples["nw"][0] > samples["nw"][2] + 18):
        raise ValueError("Stage330 northwest red contribution is absent")
    if not (samples["ne"][1] > samples["ne"][0] + 18 and
            samples["ne"][1] > samples["ne"][2] + 18):
        raise ValueError("Stage330 northeast green contribution is absent")
    if not (samples["sw"][2] > samples["sw"][0] + 18 and
            samples["sw"][2] > samples["sw"][1] + 18):
        raise ValueError("Stage330 southwest blue contribution is absent")
    if min(samples["se"]) < 105:
        raise ValueError("Stage330 southeast white contribution is absent")

    outside = (tuple(pixels[max(0, cx - 80), cy]),
               tuple(pixels[min(1279, cx + 80), cy]))
    if any(_close_rgb(color, (128, 128, 128), 10) for color in outside):
        raise ValueError("Stage330 tile quadrants collapse to a flat midpoint")

    source_left = tuple(pixels[max(0, cx - 130), cy])
    source_right = tuple(pixels[min(1279, cx + 130), cy])
    if not (source_left[0] >= 80 and source_left[2] >= 80 and
            source_left[1] <= 40):
        raise ValueError("Stage330 source-texture remainder is absent on the left")
    if not (source_right[1] >= 210 and source_right[0] >= 80 and
            source_right[2] >= 80):
        raise ValueError("Stage330 source-texture remainder is absent on the right")
    return {
        "center_x": cx, "center_y": cy,
        "midpoint_rgb": list(center),
        "midpoint_cluster_pixels": center_count,
        "horizontal_green_delta": right[1] - left[1],
        "vertical_blue_delta": bottom[2] - top[2],
        "quadrant_samples": {key: list(value) for key, value in samples.items()},
        "outside_tile_samples": [list(value) for value in outside],
        "source_remainder_samples": {
            "left": list(source_left), "right": list(source_right),
        },
    }


def audit(folder: Path) -> dict:
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage330 evidence folder invalid")
    origin = json.loads(_regular(folder / "generated-input.json"))
    if not _valid_origin(origin):
        raise ValueError("Stage330 synthetic input provenance mismatch")
    if not _valid_marker(_regular(folder / MARKER)):
        raise ValueError("Stage330 native mixed-partition upload receipt mismatch")
    frames = {name: _frame(folder / name) for name in FRAMES}
    with Image.open(io.BytesIO(_regular(folder / FRAMES[0], 12 * 1024 * 1024))) as first, \
         Image.open(io.BytesIO(_regular(folder / FRAMES[1], 12 * 1024 * 1024))) as later:
        a, b = first.convert("RGB"), later.convert("RGB")
    if ImageChops.difference(a, b).getbbox() is None:
        raise ValueError("Stage330 captured duplicate GPU frames")
    if (abs(frames[FRAMES[0]]["center_x"] - frames[FRAMES[1]]["center_x"]) > 2 or
            abs(frames[FRAMES[0]]["center_y"] - frames[FRAMES[1]]["center_y"]) > 2):
        raise ValueError("Stage330 GPU patch center drifted between captures")
    return {
        "schema": "foj.stage330.real_neixium_mixed_partition_gpu.v1",
        "generated_only": True,
        "native_upload_receipt_verified": True,
        "real_neixium_frames_verified": 2,
        "gpu_tile_midpoint_verified": True,
        "horizontal_and_vertical_linear_interpolation_verified": True,
        "tile_texture_sampling_verified": True,
        "four_quadrant_contributions_verified": True,
        "source_remainder_texture_verified": True,
        "ordered_source_then_tile_sections_verified": True,
        "frames": frames,
        "original_ps3_assets_used": False,
        "user_dds_files_read": False,
        "physical_switch_verified": False,
    }


def publish(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    if (output.exists() or output.is_symlink() or
            not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage330 public output must be a new directory")
    _check_tree(source, SOURCE_FILES)
    checked = audit(source / "bridge")
    saved = json.loads(_regular(source / "bridge" / RECEIPT))
    if checked != saved:
        raise ValueError("Stage330 saved receipt differs from fresh screenshot audit")
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n",
                        _regular(source / "nexium-archive.sha256")):
        raise ValueError("Stage330 NeXium archive checksum malformed")
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
            raise ValueError("Stage330 public export fails independent re-audit")
        for relative in PUBLIC_FILES:
            limit = 12 * 1024 * 1024 if relative.endswith(".png") else 65536
            if _regular(source / relative, limit) != _regular(output / relative, limit):
                raise ValueError("Stage330 public export changed source bytes")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema": "foj.stage330.public_generated_only_gpu_evidence.v1",
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
        print("Stage330 independent mixed-partition GPU evidence refused.", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
