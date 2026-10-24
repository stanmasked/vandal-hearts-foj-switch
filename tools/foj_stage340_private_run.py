#!/usr/bin/env python3
"""Owner-local Stage340 run against one DDS. Never publish this report or source."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import stat
import struct
import subprocess
import time


from tools.foj_stage340_receipt import MARKER, EXPECTED_PROGRESS, MARKER_NAME, PROGRESS_NAME

SCHEMA = "foj.stage340.owner_private_original_dds_gpu_roundtrip.v1"
WIDTH = HEIGHT = 256
DDS_BYTES = 128 + WIDTH * HEIGHT * 4
REPO_ROOT = Path(__file__).resolve().parents[1]


def under(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def private_source(path: Path) -> tuple[bytes, dict, str]:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or under(path.resolve(), REPO_ROOT):
        raise ValueError("Stage340 source must be a regular owner-local file outside the checkout")
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size != DDS_BYTES:
        raise ValueError("Stage340 source does not match the bounded 256x256 DDS envelope")
    blob = path.read_bytes()
    after = path.stat()
    if len(blob) != DDS_BYTES or sha(blob) != sha(path.read_bytes()):
        raise ValueError("Stage340 source changed while being read")
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size, after.st_mtime_ns, after.st_ino
    ):
        raise ValueError("Stage340 source identity changed while being read")
    if blob[:4] != b"DDS " or struct.unpack_from("<I", blob, 4)[0] != 124:
        raise ValueError("Stage340 source DDS header is invalid")
    if struct.unpack_from("<I", blob, 76)[0] != 32:
        raise ValueError("Stage340 source pixel format header is invalid")
    pf_flags, fourcc, bits = struct.unpack_from("<III", blob, 80)
    masks = struct.unpack_from("<IIII", blob, 92)
    width = struct.unpack_from("<I", blob, 16)[0]
    height = struct.unpack_from("<I", blob, 12)[0]
    mips = struct.unpack_from("<I", blob, 28)[0]
    flags = struct.unpack_from("<I", blob, 8)[0]
    pitch = struct.unpack_from("<I", blob, 20)[0]
    caps = struct.unpack_from("<I", blob, 108)[0]
    canonical = flags == 0x100F and pitch == WIDTH * 4 and caps == 0x1000
    owner_profile = flags == 0x1007 and pitch == 0 and caps == 0x1002
    if (width, height, mips, pf_flags, fourcc, bits, masks) != (
        WIDTH, HEIGHT, 0, 0x41, 0, 32,
        (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    ) and (width, height, mips, pf_flags, fourcc, bits, masks) != (
        WIDTH, HEIGHT, 1, 0x41, 0, 32,
        (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    ):
        raise ValueError("Stage340 source format or dimensions unsupported")
    if not (canonical or owner_profile):
        raise ValueError("Stage340 source DDS header contract is unsupported")
    if any(struct.unpack_from("<I", blob, p)[0] for p in (112, 116, 120, 124)):
        raise ValueError("Stage340 source has unsupported reserved header fields")
    # Independent direct BGRA8 channel-order reference. Stage334 separately
    # established exact Stage332 C-vs-Pillow base-mip parity for the full corpus.
    payload = blob[128:]
    rgba = bytearray(len(payload))
    for offset in range(0, len(payload), 4):
        rgba[offset:offset+4] = bytes((
            payload[offset+2], payload[offset+1],
            payload[offset], payload[offset+3]
        ))
    decoded_hash = sha(bytes(rgba))
    info = {
        "source_bytes": len(blob),
        "width": WIDTH,
        "height": HEIGHT,
        "format": "BGRA8",
        "mip_levels": 1,
        "decoded_rgba_sha256_reference": decoded_hash,
    }
    return blob, info, sha(blob)


def read_progress(path: Path) -> bool:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 512:
        return False
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        return False
    values = []
    for line in lines:
        if not line.startswith("FOJ340P1 stage=") or len(line) != len("FOJ340P1 stage=00"):
            return False
        try:
            values.append(int(line[-2:]))
        except ValueError:
            return False
    return tuple(values) == EXPECTED_PROGRESS


def write_report(path: Path, report: dict) -> None:
    path = Path(path)
    if path.is_symlink() or path.exists() or not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError("Stage340 private report must be a new file outside the checkout")
    if under(path.resolve(strict=False), REPO_ROOT):
        raise ValueError("Stage340 private report must be stored outside the checkout")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
        out.flush()
        os.fsync(out.fileno())


def run(source: Path, nexium: Path, nro: Path, data_root: Path,
        report_path: Path, timeout_seconds: int = 180,
        ld_library_path: Path | None = None,
        vulkan_icd: Path | None = None) -> dict:
    blob, info, source_hash = private_source(source)
    source = Path(source).resolve()
    nexium_input, nro_input = Path(nexium), Path(nro)
    if nexium_input.is_symlink() or nro_input.is_symlink():
        raise ValueError("Stage340 NeXium or NRO path may not be a symlink")
    nexium, nro = nexium_input.resolve(), nro_input.resolve()
    data_root, report_path = Path(data_root).absolute(), Path(report_path).absolute()
    if not nexium.is_file() or not os.access(nexium, os.X_OK):
        raise ValueError("Stage340 NeXium executable is missing or invalid")
    if nro.is_symlink() or not nro.is_file() or nro.stat().st_size < 0x14:
        raise ValueError("Stage340 NRO is missing or invalid")
    with nro.open("rb") as handle:
        handle.seek(0x10)
        if handle.read(4) != b"NRO0":
            raise ValueError("Stage340 NRO signature is invalid")
    if under(nro.resolve(), REPO_ROOT):
        raise ValueError("Stage340 NRO must be staged outside the checkout")
    if data_root.is_symlink() or data_root.exists() or under(data_root.resolve(strict=False), REPO_ROOT):
        raise ValueError("Stage340 private runtime root must be a new directory outside the checkout")
    data_root.mkdir(mode=0o700)
    sd = data_root / "sdmc"
    gpu = sd / "switch" / "foj" / "gpu"
    gpu.mkdir(parents=True, mode=0o700)
    source_copy = gpu / "source.dds"
    with source_copy.open("xb") as out:
        out.write(blob)
        out.flush()
        os.fsync(out.fileno())
    if sha(source_copy.read_bytes()) != source_hash:
        raise ValueError("Stage340 private SD source copy differs from input")
    marker = gpu / MARKER_NAME
    progress = gpu / PROGRESS_NAME
    if marker.exists() or marker.is_symlink() or progress.exists() or progress.is_symlink():
        raise ValueError("Stage340 refuses stale guest success or progress markers")

    env = os.environ.copy()
    env["NEXIUM_DATA_ROOT"] = str(data_root)
    if ld_library_path is not None:
        ld_path = Path(ld_library_path)
        if ld_path.is_symlink() or not ld_path.is_dir():
            raise ValueError("Stage340 Vulkan runtime library directory is invalid")
        env["LD_LIBRARY_PATH"] = str(ld_path.resolve()) + (
            ":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""
        )
    if vulkan_icd is not None:
        icd_path = Path(vulkan_icd)
        if icd_path.is_symlink() or not icd_path.is_file():
            raise ValueError("Stage340 Vulkan ICD file is invalid")
        env["VK_ICD_FILENAMES"] = str(icd_path.resolve())
    proc = subprocess.Popen(
        [str(nexium), str(nro)],
        cwd=str(REPO_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    success = False
    try:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if marker.is_file() and not marker.is_symlink():
                if marker.read_bytes() != MARKER:
                    raise ValueError("Stage340 private native receipt mismatch")
                if not read_progress(progress):
                    raise ValueError("Stage340 private native progress sequence incomplete")
                success = True
                break
            if proc.poll() is not None:
                raise RuntimeError("Stage340 guest exited without a verified GPU readback receipt")
            time.sleep(0.5)
        if not success:
            last_stage = "none"
            if progress.is_file() and not progress.is_symlink() and progress.stat().st_size <= 512:
                lines = progress.read_text(encoding="ascii", errors="ignore").splitlines()
                if lines and len(lines[-1]) == len("FOJ340P1 stage=00") and lines[-1].startswith("FOJ340P1 stage="):
                    last_stage = lines[-1][-2:]
            raise RuntimeError(f"Stage340 guest timed out; bounded last stage={last_stage}")
    finally:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=2)

    if sha(Path(source).read_bytes()) != source_hash or sha(source_copy.read_bytes()) != source_hash:
        raise ValueError("Stage340 original input or private SD copy changed during the run")
    report = {
        "schema": SCHEMA,
        "owner_private": True,
        "original_ps3_dds_used": True,
        "source_sha256": source_hash,
        **info,
        "native_guest_receipt_verified": True,
        "native_guest_progress_sequence_verified": True,
        "stage332_decode_uploaded_by_stage336": True,
        "native_gpu_image_readback_matches_stage332_rgba_byte_for_byte": True,
        "different_channels": 0,
        "source_and_sd_copy_unchanged": True,
        "stage334_independent_cpu_parity_baseline": "1479/1479 base-mip DDS images exact against Pillow",
        "framebuffer_verified": False,
        "physical_switch_verified": False,
    }
    write_report(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dds", type=Path, required=True)
    parser.add_argument("--nexium", type=Path, required=True)
    parser.add_argument("--nro", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--private-report", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--ld-library-path", type=Path)
    parser.add_argument("--vulkan-icd", type=Path)
    args = parser.parse_args()
    try:
        run(args.source_dds, args.nexium, args.nro, args.data_root,
            args.private_report, args.timeout_seconds,
            args.ld_library_path, args.vulkan_icd)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))
    print("STAGE340_OWNER_PRIVATE_ORIGINAL_DDS_GPU_READBACK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
