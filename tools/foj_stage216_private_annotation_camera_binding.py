#!/usr/bin/env python3
"""Stage216: privately bind annotated frames and source PNGs to a locked C camera.

This tool verifies local research image identity and operator-declared
annotations, NOT the provenance of original PS3 gameplay or fidelity.
Never upload operator files, receipts or extracted media to public CI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from tools.foj_stage196_private_pose_observations import (
    MAX_BYTES, only_keys, private_read, rejected
)
from tools.foj_stage203_private_actor_evidence import safe_destination
from tools.foj_stage204_private_frame_landmarks import (
    inspect_landmarks, read_bindings
)
from tools.foj_stage205_private_source_png import inspect_sources
from tools.foj_stage215_private_camera_choice_lock import verify_choice

SCHEMA = "foj.stage216.private_locked_camera_annotations.v1"
REPORT = "foj.stage216.private_annotation_camera_audit.v1"
FIELDS = {
    "schema", "camera_lock_sha256_private", "camera_receipt_sha256_private",
    "operator_observations_sha256_private",
    "research_frame_bindings_sha256_private",
    "source_png_manifest_sha256_private",
    "frames_bound", "locked_camera_verified_before_annotations",
    "operator_declared_both_captures_recorded",
    "source_png_pixels_verified_locally",
    "research_wire_landmarks_verified_locally",
    "original_ps3_capture_authenticated",
    "original_game_animation_fidelity_verified",
}


def private_digest(path: Path) -> str:
    """Hash bounded private bytes from one descriptor, without link traversal.

    Opening first and validating the descriptor avoids the lstat/read race:
    an attacker must not be able to swap a checked regular file for a
    symlink to a different local resource before the contents are read.
    O_NONBLOCK prevents waiting on a substituted FIFO before fstat rejects it.
    """
    fd = -1
    try:
        fd = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
            getattr(os, "O_NONBLOCK", 0)
        )
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or not 1 <= st.st_size <= MAX_BYTES:
            raise rejected()
        with os.fdopen(fd, "rb") as stream:
            fd = -1
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) != st.st_size:
            raise rejected()
        return hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError):
        raise rejected() from None
    finally:
        if fd >= 0:
            os.close(fd)


def evidence_witness(preview_root: Path, camera_lock: Path,
                     stage203_root: Path, observations: Path,
                     frame_bindings: Path, source_manifest: Path,
                     source_dir: Path) -> dict:
    inputs = {
        "camera_lock_sha256_private": camera_lock,
        "camera_receipt_sha256_private":
            stage203_root / "private-research-camera.json",
        "operator_observations_sha256_private": observations,
        "research_frame_bindings_sha256_private": frame_bindings,
        "source_png_manifest_sha256_private": source_manifest,
    }
    before = {name: private_digest(path) for name, path in inputs.items()}

    # The selected native renderer, all nine native frames, contact sheet,
    # camera metadata and staged rig/BANIM bytes must still be locked.
    verified = verify_choice(preview_root, camera_lock, stage203_root)
    if verified["matched_native_frames"] != 9:
        raise rejected()

    observations_data = private_read(observations)
    binding_data = read_bindings(frame_bindings)
    source_data = private_read(source_manifest)
    local_frames = inspect_landmarks(
        observations_data, binding_data, stage203_root / "private-frames"
    )
    source_frames = inspect_sources(observations_data, source_data, source_dir)
    if (local_frames["research_landmarks_near_actual_native_ppm_wire"]
            is not True or
        source_frames["png_bytes_dimensions_timestamps_match_private_manifest"]
            is not True or
        local_frames["stage203_named_frames_bound"] !=
            source_frames["source_png_frames_locally_bound"] or
        local_frames["operator_declared_both_captures_recorded"] is not True or
        source_frames["operator_claimed_source_recorded"] is not True):
        raise rejected()

    # Fail closed if inputs or owner-local captures change during comparison.
    after = {name: private_digest(path) for name, path in inputs.items()}
    if after != before:
        raise rejected()
    inspect_sources(observations_data, source_data, source_dir)
    verify_choice(preview_root, camera_lock, stage203_root)
    if {name: private_digest(path) for name, path in inputs.items()} != before:
        raise rejected()
    return {
        "schema": SCHEMA,
        **before,
        "frames_bound": local_frames["stage203_named_frames_bound"],
        "locked_camera_verified_before_annotations": True,
        "operator_declared_both_captures_recorded": True,
        "source_png_pixels_verified_locally": True,
        "research_wire_landmarks_verified_locally": True,
        "original_ps3_capture_authenticated": False,
        "original_game_animation_fidelity_verified": False,
    }


def receipt(preview_root: Path, camera_lock: Path, stage203_root: Path,
            observations: Path, frame_bindings: Path, source_manifest: Path,
            source_dir: Path, output: Path) -> dict:
    safe_destination(output)
    witness = evidence_witness(
        preview_root, camera_lock, stage203_root, observations,
        frame_bindings, source_manifest, source_dir
    )
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = -1
            json.dump(witness, stream, sort_keys=True, indent=2,
                      allow_nan=False)
            stream.write("\n")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    finally:
        if fd >= 0:
            os.close(fd)
    return public_result(witness, "annotation_camera_binding_locked_privately")


def check(preview_root: Path, camera_lock: Path, stage203_root: Path,
          observations: Path, frame_bindings: Path, source_manifest: Path,
          source_dir: Path, output: Path) -> dict:
    # Pin the private receipt itself throughout verification. A replacement
    # with a still-valid receipt must not be accepted after the earlier read.
    # Check link status and a bounded raw-byte digest on both sides.
    before_receipt = private_digest(output)
    prior = private_read(output)
    only_keys(prior, FIELDS)
    if private_digest(output) != before_receipt:
        raise rejected()
    witness = evidence_witness(
        preview_root, camera_lock, stage203_root, observations,
        frame_bindings, source_manifest, source_dir
    )
    if prior != witness or private_digest(output) != before_receipt:
        raise rejected()
    return public_result(witness, "annotation_camera_binding_reverified")


def public_result(witness: dict, positive: str) -> dict:
    return {
        "schema": REPORT,
        positive: True,
        "locally_bound_frame_count": witness["frames_bound"],
        "images_annotations_camera_or_hashes_exported": False,
        "original_ps3_capture_authenticated": False,
        "original_game_animation_fidelity_verified": False,
        "warning": (
            "This is consistency of owner-declared captures, annotations "
            "and native C research frames, not authenticated PS3 footage, "
            "original camera recovery or verified game animation."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--bind", action="store_true")
    mode.add_argument("--verify", action="store_true")
    for label in ("preview-root", "camera-lock", "stage203-root",
                  "observations", "frame-bindings", "source-manifest",
                  "source-dir", "binding-receipt"):
        parser.add_argument("--" + label, type=Path, required=True)
    args = parser.parse_args(argv)
    paths = (args.preview_root, args.camera_lock, args.stage203_root,
             args.observations, args.frame_bindings, args.source_manifest,
             args.source_dir, args.binding_receipt)
    try:
        report = (receipt(*paths) if args.bind else check(*paths))
    except (OSError, ValueError, TypeError, IndexError, OverflowError):
        print("Private Stage216 camera/annotation binding rejected.",
              file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
