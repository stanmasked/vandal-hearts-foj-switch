#!/usr/bin/env python3
"""Owner-local Stage342 run. Keeps source, frames, logs and report outside checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import time

from PIL import Image, ImageChops

from tools.foj_stage340_private_run import REPO_ROOT, private_source, write_report
from tools.foj_stage342_nexium_display import install as install_display
from tools.foj_stage342_frame_gate import (
    MARKER, MARKER_NAME, audit_frames, decode_bgra8_dds,
)


def under(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def sha_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage342 checksum input must be a regular file")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(source: Path, nexium: Path, nro: Path, shader_dir: Path,
        data_root: Path, evidence: Path, report_path: Path,
        timeout_seconds: int = 180, ld_library_path: Path | None = None,
        vulkan_icd: Path | None = None) -> dict:
    source = Path(source)
    blob, source_info, source_hash = private_source(source)
    source = source.resolve()
    nexium, nro, shader_dir = Path(nexium), Path(nro), Path(shader_dir)
    data_root, evidence, report_path = (
        Path(data_root).absolute(), Path(evidence).absolute(), Path(report_path).absolute()
    )
    for path, label in ((data_root, "runtime root"), (evidence, "evidence folder"),
                        (report_path, "report")):
        if path.is_symlink() or path.exists() or under(path.resolve(strict=False), REPO_ROOT):
            raise ValueError(f"Stage342 {label} must be new and outside the checkout")
    if not report_path.parent.is_dir() or report_path.parent.is_symlink():
        raise ValueError("Stage342 report parent must already be a regular private directory")
    if (data_root == evidence or data_root in evidence.parents or evidence in data_root.parents
            or report_path == evidence or under(report_path, evidence)
            or under(report_path, data_root)):
        raise ValueError("Stage342 runtime, evidence and report paths must remain separate")
    if (nexium.is_symlink() or not nexium.is_file() or
            not os.access(nexium, os.X_OK) or under(nexium.resolve(), REPO_ROOT)):
        raise ValueError("Stage342 NeXium launcher must be a regular executable outside the checkout")
    if nro.is_symlink() or not nro.is_file() or under(nro.resolve(), REPO_ROOT):
        raise ValueError("Stage342 NRO must be a regular file outside the checkout")
    with nro.open("rb") as handle:
        handle.seek(0x10)
        if handle.read(4) != b"NRO0":
            raise ValueError("Stage342 NRO signature invalid")
    if (shader_dir.is_symlink() or not shader_dir.is_dir() or
            under(shader_dir.resolve(), REPO_ROOT)):
        raise ValueError("Stage342 shader directory must be regular and outside the checkout")
    shaders = {}
    for name in ("foj_actor.vert.dksh", "foj_triangle.frag.dksh"):
        item = shader_dir / name
        if item.is_symlink() or not item.is_file() or item.stat().st_size == 0:
            raise ValueError(f"Stage342 required generated shader missing: {name}")
        shaders[name] = item.read_bytes()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", nexium.name):
        raise ValueError("Stage342 NeXium launcher name is not safe for evidence metadata")

    data_root.mkdir(mode=0o700)
    install_display(data_root)
    evidence.mkdir(mode=0o700)
    sd = data_root / "sdmc"
    gpu = sd / "switch" / "foj" / "gpu"
    gpu.mkdir(parents=True, mode=0o700)
    source_copy = gpu / "source.dds"
    with source_copy.open("xb") as out:
        out.write(blob)
        out.flush()
        os.fsync(out.fileno())
    staged_copy_hash_before = sha_file(source_copy)
    if staged_copy_hash_before != source_hash:
        raise ValueError("Stage342 private SD source copy differs from source")
    reference_rgba = decode_bgra8_dds(source_copy.read_bytes())
    reference_hash = hashlib.sha256(reference_rgba).hexdigest()
    if reference_hash != source_info["decoded_rgba_sha256_reference"]:
        raise ValueError("Stage342 independent CPU references disagree on the source DDS")
    del reference_rgba
    for name, payload in shaders.items():
        target = gpu / name
        with target.open("xb") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
    marker = gpu / MARKER_NAME
    if marker.exists() or marker.is_symlink():
        raise ValueError("Stage342 refuses a stale guest marker")

    runtime_hash = sha_file(nexium)
    nro_hash_before = sha_file(nro)
    checksum_path = evidence / "nexium-runtime.sha256"
    checksum_path.write_text(
        f"{runtime_hash}  {nexium.name}\n", encoding="ascii"
    )
    guest_log = evidence / "guest.log"
    if shutil.which("xdotool") is None:
        raise ValueError("Stage342 requires xdotool for real window capture")
    import_bin = shutil.which("import")
    magick_bin = shutil.which("magick")
    if import_bin is None and magick_bin is None:
        raise ValueError("Stage342 requires ImageMagick import or magick for real window capture")

    def capture_window(window_id: str, destination: Path) -> None:
        command = (
            [import_bin, "-window", window_id, str(destination)]
            if import_bin is not None else
            [magick_bin, "import", "-window", window_id, str(destination)]
        )
        subprocess.run(command, timeout=12, check=True)

    env = os.environ.copy()
    env["NEXIUM_DATA_ROOT"] = str(data_root)
    if ld_library_path is not None:
        library_path = Path(ld_library_path)
        if (library_path.is_symlink() or not library_path.is_dir() or
                under(library_path.resolve(), REPO_ROOT)):
            raise ValueError("Stage342 bundled runtime library directory must be outside the checkout")
        env["LD_LIBRARY_PATH"] = str(library_path.resolve()) + (
            ":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""
        )
    if vulkan_icd is not None:
        icd = Path(vulkan_icd)
        if (icd.is_symlink() or not icd.is_file() or
                under(icd.resolve(), REPO_ROOT)):
            raise ValueError("Stage342 Vulkan ICD file must be regular and outside the checkout")
        env["VK_ICD_FILENAMES"] = str(icd.resolve())

    command = [str(nexium.resolve()), str(nro.resolve())]
    if not env.get("DISPLAY"):
        xvfb = shutil.which("xvfb-run")
        if not xvfb:
            raise ValueError("Stage342 needs DISPLAY or xvfb-run")
        command = [xvfb, "-a", "-s", "-screen 0 1280x720x24", *command]

    with guest_log.open("xb") as log:
        proc = subprocess.Popen(
            command, cwd=str(REPO_ROOT), env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        success = False
        window = ""
        try:
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError("Stage342 NeXium exited before its native sample receipt")
                if not window:
                    search = subprocess.run(
                        ["xdotool", "search", "--onlyvisible", "--name", "NeXium"],
                        capture_output=True, text=True, timeout=5, check=False,
                    )
                    if search.returncode == 0:
                        candidates = search.stdout.splitlines()
                        if candidates:
                            window = candidates[-1].strip()
                if marker.is_file() and not marker.is_symlink():
                    if marker.read_bytes() != MARKER:
                        raise ValueError("Stage342 native sample receipt mismatch")
                    if not window:
                        raise ValueError("Stage342 receipt exists but no real NeXium window is visible")
                    window_pid = subprocess.run(
                        ["xdotool", "getwindowpid", window],
                        capture_output=True, text=True, timeout=5, check=False,
                    )
                    pid = window_pid.stdout.strip()
                    if window_pid.returncode != 0 or not pid.isdigit():
                        raise ValueError("Stage342 cannot bind the framebuffer window to a process")
                    args = subprocess.run(
                        ["ps", "-o", "args=", "-p", pid],
                        capture_output=True, text=True, timeout=5, check=False,
                    ).stdout
                    if "nexium" not in args.lower():
                        raise ValueError("Stage342 capture window is not owned by NeXium")
                    success = True
                    break
                time.sleep(0.5)
            if not success:
                raise RuntimeError("Stage342 timed out waiting for a verified native sample receipt")
            # Capture after the NRO's post-present receipt; never synthesize frames.
            time.sleep(1)
            for name in ("gpu-initial.png", "gpu-later.png", "gpu-later-candidate.png"):
                if (evidence / name).exists() or (evidence / name).is_symlink():
                    raise ValueError("Stage342 refuses stale capture output")
            first_frame = evidence / "gpu-initial.png"
            later_frame = evidence / "gpu-later.png"
            candidate = evidence / "gpu-later-candidate.png"
            if candidate.exists() or candidate.is_symlink():
                raise ValueError("Stage342 refuses a stale candidate frame")
            capture_window(window, first_frame)
            # The scene intentionally alternates its clear phase every frame.
            # Capture until that phase changes instead of assuming a 1-second
            # delay lands on the opposite parity of a vsynced presentation loop.
            distinct = False
            for _ in range(60):
                if proc.poll() is not None:
                    raise RuntimeError("Stage342 NeXium exited between independent captures")
                capture_window(window, candidate)
                with Image.open(first_frame) as first, Image.open(candidate) as later:
                    if first.size != later.size:
                        raise ValueError("Stage342 candidate frame dimensions changed")
                    distinct = ImageChops.difference(
                        first.convert("RGB"), later.convert("RGB")
                    ).getbbox() is not None
                if distinct:
                    if later_frame.exists() or later_frame.is_symlink():
                        raise ValueError("Stage342 refuses a stale second capture")
                    os.replace(candidate, later_frame)
                    break
                candidate.unlink()
                time.sleep(0.05)
            if not distinct or not later_frame.is_file() or later_frame.is_symlink():
                raise RuntimeError("Stage342 could not capture a distinct presented frame")
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

    audit = audit_frames(source_copy, sd, evidence, require_generated_metadata=False)
    # Re-hash only after the frame audit has consumed the staged source so a
    # mutation during either capture or reference comparison is detected.
    source_hash_after = sha_file(source)
    staged_copy_hash_after = sha_file(source_copy)
    nro_hash_after = sha_file(nro)
    runtime_hash_after = sha_file(nexium)
    if (source_hash_after != source_hash or
            staged_copy_hash_after != staged_copy_hash_before or
            nro_hash_after != nro_hash_before or
            runtime_hash_after != runtime_hash):
        raise ValueError("Stage342 source, staged copy, NRO or runtime changed during the run")
    report = {
        "schema": "foj.stage342.owner_private_original_dds_shader_frame.v1",
        "owner_private": True,
        "source_sha256": source_hash,
        "source_sha256_before": source_hash,
        "source_sha256_after": source_hash_after,
        "staged_copy_sha256_before": staged_copy_hash_before,
        "staged_copy_sha256_after": staged_copy_hash_after,
        "decoded_rgba_sha256_reference": source_info["decoded_rgba_sha256_reference"],
        "frame_gate_decoded_rgba_sha256": reference_hash,
        "cpu_reference_parity_verified": True,
        "source_format": source_info["format"],
        "source_width": source_info["width"],
        "source_height": source_info["height"],
        "source_bytes": source_info["source_bytes"],
        "source_unchanged": source_hash_after == source_hash,
        "staged_copy_unchanged": staged_copy_hash_after == staged_copy_hash_before,
        "nro_sha256": nro_hash_after,
        "nro_sha256_before": nro_hash_before,
        "nro_sha256_after": nro_hash_after,
        "nexium_launcher_sha256": runtime_hash_after,
        "nexium_launcher_sha256_before": runtime_hash,
        "nexium_launcher_sha256_after": runtime_hash_after,
        "native_receipt_verified": True,
        "real_window_pid_verified": True,
        "framebuffer_audit": audit,
        "physical_switch_verified": False,
        "full_game_fidelity_verified": False,
    }
    write_report(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--nexium", type=Path, required=True)
    parser.add_argument("--nro", type=Path, required=True)
    parser.add_argument("--shader-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--ld-library-path", type=Path)
    parser.add_argument("--vulkan-icd", type=Path)
    args = parser.parse_args()
    try:
        result = run(
            args.source, args.nexium, args.nro, args.shader_dir,
            args.data_root, args.evidence, args.report, args.timeout,
            args.ld_library_path, args.vulkan_icd,
        )
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))
    # Owner-local only. This output intentionally includes private checksums
    # and sample pixels; never pipe it to public CI or a public log.
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
