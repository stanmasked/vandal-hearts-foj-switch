#!/usr/bin/env python3
"""Stage286: owner-local three-DDS binding to the *generated* research actor.

Private source DDS bytes are never printed, published, extracted from a PKG,
or copied into public CI. Only canonical DDS supported by the existing
native atlas loader are accepted. Output is a NEW private SD directory.
This does not establish original PS3 formats, materials or Switch playback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys

from tools.foj_fd_bound_reader import READ, NOFOLLOW, DIRECTORY, _identity, open_regular_at, open_regular_beneath
from tools.foj_gpu_local_dds_preflight import classify_classic_dds, MAX_FILE_BYTES
from tools.foj_stage273_dynamic_gpu_sd import install_dynamic, generated_actor
from tools.foj_stage267_generated_multiblend_sd import SUBDIR, generated_three_layer_materials
from tools.foj_stage260_generated_gpu_sd import SHADERS

SCHEMA = "foj.stage286.private_three_dds_material_binding.v1"
SLOTS = ("material0.dds", "material1.dds", "material2.dds")
GEOMETRY = "actor.fojrm"
MATERIALS = "actor.fojmat"
MANIFEST = "owner-private-stage286-binding.json"
PRIVATE_REPO_FOLDERS = frozenset(("local-data", "game-data", "foj-local", "extracted"))
MAX_RECEIPT_BYTES = 16384


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_under(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def _destination_guard(source: Path, root: Path) -> None:
    """Refuse creating game-derived data in tracked portions of this repo."""
    if not NOFOLLOW or not DIRECTORY:
        raise ValueError("Stage286 requires secure local no-follow opens")
    if root.exists() or root.is_symlink() or not root.parent.is_dir():
        raise ValueError("Stage286 destination must be a new private directory")
    destination = root.absolute()
    source_absolute = source.absolute()
    if (_is_under(destination, source_absolute) or
            _is_under(source_absolute, destination)):
        raise ValueError("Stage286 source and output directories must be separate")
    for parent in (destination.parent, *destination.parent.parents):
        if parent.is_symlink():
            raise ValueError("Stage286 private destination has a symlink ancestor")
    repo = Path(__file__).resolve().parents[1]
    if _is_under(destination, repo):
        relative = destination.relative_to(repo)
        if not relative.parts or relative.parts[0] not in PRIVATE_REPO_FOLDERS:
            raise ValueError("Stage286 refuses private DDS output in a tracked project path")


def _read_exact_slots(source: Path) -> tuple[tuple[bytes, ...], tuple[dict, ...]]:
    if not isinstance(source, Path) or not NOFOLLOW or not DIRECTORY:
        raise ValueError("Stage286 requires a private source directory")
    try:
        root_fd = os.open(source, READ | NOFOLLOW | DIRECTORY)
    except OSError:
        raise ValueError("Unable to safely open Stage286 private source") from None
    try:
        directory_start = os.fstat(root_fd)
        textures = []
        descriptions = []
        for index, name in enumerate(SLOTS):
            try:
                before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            except OSError:
                raise ValueError("Stage286 requires all three regular DDS inputs") from None
            if not stat.S_ISREG(before.st_mode) or not 128 <= before.st_size <= MAX_FILE_BYTES:
                raise ValueError("Stage286 source DDS is not a bounded regular file")
            with open_regular_at(root_fd, name) as (stream, opened):
                if _identity(before) != _identity(opened):
                    raise ValueError("Stage286 source entry changed")
                data = stream.read(opened.st_size + 1)
                stream.seek(0)
                replay = stream.read(opened.st_size + 1)
                if (len(data) != opened.st_size or data != replay or
                        len(replay) != opened.st_size):
                    raise ValueError("Stage286 source bytes changed during read")
                try:
                    final = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
                except OSError:
                    raise ValueError("Stage286 source entry changed") from None
                if _identity(before) != _identity(final):
                    raise ValueError("Stage286 source entry changed")
                layout = classify_classic_dds(data)
            if index == 2:
                # Conservative opaque rear guard. Native GPU checks decoded
                # rear alpha; until BCn block-alpha parity is separately proven,
                # only explicitly opaque 32-bit RGBA/BGRA can occupy slot 2.
                if layout["format"] not in ("RGBA8", "BGRA8"):
                    raise ValueError("Stage286 rear atlas must use opaque RGBA8/BGRA8")
                if any(value != 255 for value in data[128 + 3::4]):
                    raise ValueError("Stage286 rear atlas contains non-opaque alpha")
            textures.append(data)
            descriptions.append({
                "slot": index, "file": name, "format": layout["format"],
                "width": layout["width"], "height": layout["height"],
                "declared_mip_levels": layout["declared_mip_levels"],
                "sha256": _hash(data), "dds_file_bytes": len(data),
            })
        if _identity(directory_start) != _identity(os.fstat(root_fd)):
            raise ValueError("Stage286 source directory changed during read")
        return tuple(textures), tuple(descriptions)
    finally:
        os.close(root_fd)


def _read_staged(root: Path, name: str, max_size: int) -> bytes:
    relative = SUBDIR / name
    with open_regular_beneath(root, relative.as_posix()) as (stream, info):
        if not 1 <= info.st_size <= max_size:
            raise ValueError("Stage286 staged entry size invalid")
        data = stream.read(info.st_size + 1)
        if len(data) != info.st_size:
            raise ValueError("Stage286 staged entry changed")
        return data


def _private_write_new(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd != -1:
            os.close(fd)


def _replace_fresh_generated(path: Path, data: bytes) -> None:
    # Only a newly generated private root is changed; not any user input.
    if path.is_symlink() or not path.is_file():
        raise ValueError("Stage286 generated slot unexpectedly changed")
    path.unlink()
    _private_write_new(path, data)


def _public_summary(manifest: dict) -> dict:
    return {
        "schema": SCHEMA,
        "mode": "owner-local-generated-geometry-private-dds",
        "material_slots_accepted": 3,
        "compatible_formats": [entry["format"] for entry in manifest["slots"]],
        "rear_alpha_opaque_checked": True,
        "local_manifest_verified": True,
        "ps3_resource_format_verified": False,
        "original_foj_material_mapping_verified": False,
        "physical_switch_gpu_verified": False,
        "source_paths_hashes_pixels_exposed": False,
        "warning": "Local private bytes must not be committed, uploaded or attached to GitHub CI.",
    }


def prepare(source: Path, shaders: Path, destination: Path) -> dict:
    """Bind exactly three user-owned compatible DDS files to invented actor."""
    source, shaders, destination = Path(source), Path(shaders), Path(destination)
    _destination_guard(source, destination)
    textures, descriptions = _read_exact_slots(source)
    # Real shader acceptance and public actor-generation contracts are
    # inherited from the already-tested Stage273 generator.
    try:
        install_dynamic(destination, shaders, "original")
        output = destination / SUBDIR
        for name, contents in zip(SLOTS, textures):
            _replace_fresh_generated(output / name, contents)
        originals = {
            GEOMETRY: generated_actor("original"),
            MATERIALS: generated_three_layer_materials(),
        }
        for filename, expected in originals.items():
            if _read_staged(destination, filename, MAX_FILE_BYTES) != expected:
                raise ValueError("Stage286 generated actor/material contract changed")
        bound_files = {}
        for filename in (*SLOTS, GEOMETRY, MATERIALS, *SHADERS):
            bound_files[filename] = _hash(
                _read_staged(destination, filename, MAX_FILE_BYTES))
        manifest = {
            "schema": SCHEMA,
            "scenario": "generated-three-layer-original",
            "source": "owner-local-fixed-dds-slots",
            "original_ps3_resource_identity_verified": False,
            "original_material_mapping_verified": False,
            "switch_gpu_verified": False,
            "rear_alpha_opaque_checked": True,
            "slots": list(descriptions),
            "bound_file_sha256": bound_files,
        }
        raw = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
        if len(raw) > MAX_RECEIPT_BYTES:
            raise ValueError("Stage286 manifest unexpectedly large")
        _private_write_new(destination / MANIFEST, raw)
        # Independently reread and compare actual staged bytes before success.
        verify(destination)
    except BaseException:
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        raise
    return _public_summary(manifest)


def verify(root: Path) -> dict:
    root = Path(root)
    with open_regular_beneath(root, MANIFEST) as (stream, st):
        if not 1 <= st.st_size <= MAX_RECEIPT_BYTES:
            raise ValueError("Stage286 owner manifest size invalid")
        data = stream.read(st.st_size + 1)
        if len(data) != st.st_size:
            raise ValueError("Stage286 owner manifest changed")
    try:
        manifest = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Stage286 owner manifest invalid") from None
    if (type(manifest) is not dict or
            set(manifest) != {"schema", "scenario", "source",
                             "original_ps3_resource_identity_verified",
                             "original_material_mapping_verified",
                             "switch_gpu_verified", "rear_alpha_opaque_checked",
                             "slots", "bound_file_sha256"} or
            manifest["schema"] != SCHEMA or
            manifest["scenario"] != "generated-three-layer-original" or
            manifest["source"] != "owner-local-fixed-dds-slots" or
            any(manifest[k] is not False for k in (
                "original_ps3_resource_identity_verified",
                "original_material_mapping_verified",
                "switch_gpu_verified")) or
            manifest["rear_alpha_opaque_checked"] is not True or
            type(manifest["slots"]) is not list or len(manifest["slots"]) != 3 or
            type(manifest["bound_file_sha256"]) is not dict or
            set(manifest["bound_file_sha256"]) !=
            set((*SLOTS, GEOMETRY, MATERIALS, *SHADERS))):
        raise ValueError("Stage286 owner manifest contract invalid")
    if _read_staged(root, GEOMETRY, MAX_FILE_BYTES) != generated_actor("original"):
        raise ValueError("Stage286 generated actor bytes changed")
    if _read_staged(root, MATERIALS, MAX_FILE_BYTES) != generated_three_layer_materials():
        raise ValueError("Stage286 generated material bindings changed")
    for index, name in enumerate(SLOTS):
        entry = manifest["slots"][index]
        if (type(entry) is not dict or
                set(entry) != {"slot", "file", "format", "width",
                              "height", "declared_mip_levels",
                              "sha256", "dds_file_bytes"} or
                type(entry["slot"]) is not int or entry["slot"] != index or
                entry["file"] != name):
            raise ValueError("Stage286 material slot metadata invalid")
        blob = _read_staged(root, name, MAX_FILE_BYTES)
        layout = classify_classic_dds(blob)
        if (entry["format"] != layout["format"] or
                entry["width"] != layout["width"] or
                entry["height"] != layout["height"] or
                entry["declared_mip_levels"] != layout["declared_mip_levels"] or
                entry["dds_file_bytes"] != len(blob) or
                entry["sha256"] != _hash(blob)):
            raise ValueError("Stage286 bound DDS identity changed")
        if index == 2:
            if layout["format"] not in ("RGBA8", "BGRA8") or any(
                a != 255 for a in blob[131::4]):
                raise ValueError("Stage286 bound rear alpha not opaque")
    for filename, expected in manifest["bound_file_sha256"].items():
        if type(expected) is not str or len(expected) != 64 or any(
                x not in "0123456789abcdef" for x in expected):
            raise ValueError("Stage286 bound file fingerprint invalid")
        actual = _hash(_read_staged(root, filename, MAX_FILE_BYTES))
        if actual != expected:
            raise ValueError("Stage286 bound file identity changed")
    return _public_summary(manifest)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare", help="Create a NEW private SD fixture")
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--shaders", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    q = commands.add_parser("verify", help="Verify already staged private DDS")
    q.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = (prepare(args.source_dir, args.shaders, args.output_root)
                  if args.command == "prepare" else verify(args.output_root))
    except (ValueError, OSError, TypeError, KeyError):
        print("Stage286 private DDS bridge rejected; review files locally. No source details published.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
