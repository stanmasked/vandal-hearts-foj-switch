#!/usr/bin/env python3
"""Stage293: real NeXium guest test of three Stage292-CONVERTED synthetic DDS.

Generated GTF-like inputs are deterministic/tagged public fixtures only.
Uses the existing Stage286 3-material SD bridge and Stage274 NeXium drive.
Neither original PS3 data nor private manifests may enter public evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

from PIL import Image, ImageChops

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET, WARM, COOL
from tools.foj_stage267_gpu_three_layer_check import BACKGROUNDS
from tools.foj_stage273_dynamic_gpu_check import inspect
from tools.foj_stage274_pass_contract_check import expected_receipt
from tools.foj_stage286_private_three_dds_material_bridge import (
    MANIFEST, SLOTS, SUBDIR, prepare as stage286_prepare, verify as stage286_verify,
)
from tools.foj_stage289_public_guest_evidence import _check_tree, _regular_file
from tools.foj_stage292_synthetic_gtf_dds_roundtrip import (
    generate_solid_fixture, convert_fixture,
)

SCHEMA = "foj.stage293.converted_synthetic_gtf_three_dds_neixum.v1"
RECEIPT = "stage293-three-converted-dds-gpu-receipt.json"
COLORS = ((*VIOLET, 128), (*WARM, 128), (*COOL, 255))
FRAMES = ("gpu-initial.png", "gpu-later.png")
PUBLIC = (
    "generated-input.json", "dds-before.json", "dds-after.json",
    *FRAMES, "native-sort-pass.txt", "native-alpha-pass.txt", RECEIPT,
)
ARCHIVE_HASH = "nexium-archive.sha256"
SOURCE_FILES = {ARCHIVE_HASH} | {"bridge/" + n for n in (*PUBLIC, "guest.log")}
EXPORT_FILES = {ARCHIVE_HASH} | {"bridge/" + n for n in PUBLIC}


def converted() -> dict[str, bytes]:
    out = {}
    for name, color in zip(SLOTS, COLORS):
        dds, note = convert_fixture(generate_solid_fixture(color))
        if (note["synthetic_fixture_mode"] != "constant-gpu-probe" or
                note["original_ps3_resources_processed"] is not False or
                note["production_game_conversion_permitted"] is not False or
                dds == generated_dds(color) or
                dds[128:] != bytes(color) * 4096):
            raise ValueError("Stage293 synthetic converter bypass or pixel mismatch")
        out[name] = dds
    return out


def hashes() -> dict[str, str]:
    return {name: hashlib.sha256(data).hexdigest()
            for name, data in converted().items()}


def _write_new(directory: Path, name: str, payload: dict) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Stage293 evidence directory must already exist")
    path = directory / name
    if path.exists() or path.is_symlink():
        raise ValueError("Stage293 existing evidence receipt")
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def _origin() -> dict:
    return {
        "schema": SCHEMA,
        "source": "three Stage292 converted synthetic-only BGRA fixtures via Stage286",
        "generated_only": True,
        "stage292_converter_executed": True,
        "original_ps3_resources": False,
        "private_binding_manifest_archived": False,
        "scenario": "original",
        "expected_native_sort": [2, 1, 0],
        "expected_converted_dds_sha256": hashes(),
    }


def _attestation(phase: str) -> dict:
    return {
        "schema": SCHEMA, "phase": phase, "material_slots_verified": 3,
        "stage292_converter_executed": True,
        "generated_only": True, "original_ps3_resources": False,
        "private_binding_manifest_archived": False,
        "dds_sha256": hashes(),
    }


def prepare(work: Path, shaders: Path, evidence: Path) -> dict:
    work, evidence = Path(work), Path(evidence)
    if (work.exists() or work.is_symlink() or
            not work.parent.is_dir() or work.parent.is_symlink() or
            evidence.exists() or evidence.is_symlink() or
            not evidence.parent.is_dir() or evidence.parent.is_symlink()):
        raise ValueError("Stage293 requires new synthetic work and evidence directories")
    work.mkdir(mode=0o700)
    try:
        inputs = work / "inputs"
        inputs.mkdir(mode=0o700)
        for name, contents in converted().items():
            with (inputs / name).open("xb") as handle:
                handle.write(contents)
        summary = stage286_prepare(inputs, shaders, work / "staged")
        if (summary["material_slots_accepted"] != 3 or
                summary["ps3_resource_format_verified"] is not False or
                summary["original_foj_material_mapping_verified"] is not False or
                summary["physical_switch_gpu_verified"] is not False or
                summary != stage286_verify(work / "staged")):
            raise ValueError("Stage293 Stage286 staging provenance disagreement")
        evidence.mkdir(mode=0o700)
        _write_new(evidence, "generated-input.json", _origin())
        return summary
    except BaseException:
        shutil.rmtree(work)
        if evidence.is_dir() and not evidence.is_symlink():
            shutil.rmtree(evidence)
        raise


def attest(work: Path, evidence: Path, phase: str) -> dict:
    if phase not in ("before", "after"):
        raise ValueError("Stage293 unknown observation phase")
    root = Path(work) / "staged"
    checked = stage286_verify(root)
    if checked["material_slots_accepted"] != 3:
        raise ValueError("Stage293 staged slot mismatch")
    for name, contents in converted().items():
        path = root / SUBDIR / name
        if path.is_symlink() or not path.is_file() or path.read_bytes() != contents:
            raise ValueError("Stage293 Stage292 converted DDS bytes changed")
    result = _attestation(phase)
    _write_new(Path(evidence), f"dds-{phase}.json", result)
    return result


def audit(evidence: Path) -> dict:
    folder = Path(evidence)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Stage293 evidence root invalid")
    def report(name: str) -> dict:
        return json.loads(_regular_file(folder / name))
    if report("generated-input.json") != _origin():
        raise ValueError("Stage293 source-to-conversion provenance mismatch")
    for phase in ("before", "after"):
        if report(f"dds-{phase}.json") != _attestation(phase):
            raise ValueError("Stage293 converted DDS identity or phase mismatch")
    markers = {
        "native-sort-pass.txt": b"FOJ_NATIVE_SORT_V1 2,1,0\n",
        "native-alpha-pass.txt": expected_receipt("original"),
    }
    for name, expected in markers.items():
        if _regular_file(folder / name) != expected:
            raise ValueError("Stage293 native guest receipt mismatch")
    for forbidden in (
        MANIFEST, "native-rear-alpha-reject.txt", "native-topology-reject.txt",
    ):
        if (folder / forbidden).exists() or (folder / forbidden).is_symlink():
            raise ValueError("Stage293 private or contradictory guest evidence")
    for name in FRAMES:
        _regular_file(folder / name, 12 * 1024 * 1024)
    first, second = (inspect(folder / name, "original") for name in FRAMES)
    with Image.open(folder / FRAMES[0]) as a, Image.open(folder / FRAMES[1]) as b:
        x, y = a.convert("RGB"), b.convert("RGB")
    if ImageChops.difference(x, y).getbbox() is None:
        raise ValueError("Stage293 duplicate guest frames")
    if sum(x.getpixel(p) != y.getpixel(p) for p in BACKGROUNDS) < 3:
        raise ValueError("Stage293 GPU clear-color phase unchanged")
    if any(first[name]["matching_pixels"] != second[name]["matching_pixels"]
           for name in first):
        raise ValueError("Stage293 changed material footprint across guest frames")
    return {
        "schema": "foj.stage293.real_guest_converted_dds_evidence.v1",
        "generated_only": True, "original_ps3_resources": False,
        "stage292_converter_executed": True, "stage286_bridge_verified": True,
        "physical_switch_verified": False, "material_slots": 3,
        "guest_frames_verified": 2, "dds_before_after_checked": True,
        "native_sort_and_alpha_pass_checked": True,
        "background_clear_phase_changed": True,
        "first": first, "later": second,
        "warning": "Actual NeXium frames; converted generated-only BGRA, not original game assets.",
    }


def publish(source: Path, output: Path) -> dict:
    source, output = Path(source), Path(output)
    if (output.exists() or output.is_symlink() or
            not output.parent.is_dir() or output.parent.is_symlink()):
        raise ValueError("Stage293 public destination must be fresh")
    _check_tree(source, SOURCE_FILES)
    checked = audit(source / "bridge")
    saved = json.loads(_regular_file(source / "bridge" / RECEIPT))
    if checked != saved:
        raise ValueError("Stage293 re-audit differs from saved guest receipt")
    archive = _regular_file(source / ARCHIVE_HASH)
    if not re.fullmatch(rb"[0-9a-f]{64}  /tmp/nexium\.tar\.gz\n", archive):
        raise ValueError("Stage293 malformed NeXium provenance checksum")
    output.mkdir(mode=0o700)
    try:
        (output / "bridge").mkdir(mode=0o700)
        for relative in sorted(EXPORT_FILES):
            src = source / relative
            content = _regular_file(src, 12 * 1024 * 1024
                                    if src.name in FRAMES else 65536)
            with (output / relative).open("xb") as target:
                target.write(content)
        _check_tree(output, EXPORT_FILES)
        if audit(output / "bridge") != checked:
            raise ValueError("Stage293 public evidence differs after export")
        for relative in EXPORT_FILES:
            src, dst = source / relative, output / relative
            limit = 12 * 1024 * 1024 if src.name in FRAMES else 65536
            if _regular_file(src, limit) != _regular_file(dst, limit):
                raise ValueError("Stage293 source bytes changed during export")
    except BaseException:
        shutil.rmtree(output)
        raise
    return {
        "schema": "foj.stage293.public_guest_export.v1",
        "generated_only": True, "original_ps3_resources": False,
        "public_files": len(EXPORT_FILES),
        "raw_guest_log_uploaded": False, "private_binding_manifest_uploaded": False,
        "guest_frames_verified": checked["guest_frames_verified"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    p = actions.add_parser("prepare")
    p.add_argument("--work-root", type=Path, required=True)
    p.add_argument("--shaders", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    a = actions.add_parser("attest")
    a.add_argument("--work-root", type=Path, required=True)
    a.add_argument("--evidence", type=Path, required=True)
    a.add_argument("--phase", choices=("before", "after"), required=True)
    v = actions.add_parser("audit")
    v.add_argument("--evidence", type=Path, required=True)
    v.add_argument("--report", type=Path, required=True)
    q = actions.add_parser("publish")
    q.add_argument("--source", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = prepare(args.work_root, args.shaders, args.evidence)
        elif args.action == "attest":
            result = attest(args.work_root, args.evidence, args.phase)
        elif args.action == "audit":
            result = audit(args.evidence)
            _write_new(args.evidence, args.report.name, result)
        else:
            result = publish(args.source, args.output)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        print("Stage293 generated-only GPU proof refused; inspect CI locally.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
