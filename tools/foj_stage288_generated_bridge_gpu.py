#!/usr/bin/env python3
"""Stage288: prove Stage286's generated-only three-DDS bridge reaches NeXium.

All three DDS are freshly created from public synthetic constants. A local
Stage286 private manifest is NEVER copied to evidence or CI artifacts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
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

SCHEMA = "foj.stage288.generated_stage286_bridge_to_neixum.v1"
COLORS = ((*VIOLET, 128), (*WARM, 128), (*COOL, 255))
ROOT_NAME = "owner-local-generated-only"
FRAMES = ("gpu-initial.png", "gpu-later.png")


def expected_hashes() -> dict[str, str]:
    return {slot: hashlib.sha256(generated_dds(c)).hexdigest()
            for slot, c in zip(SLOTS, COLORS)}


def _new_public_report(folder: Path, name: str, payload: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    if target.exists() or target.is_symlink():
        raise ValueError("Stage288 existing public witness")
    target.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")


def prepare(work: Path, shaders: Path, evidence: Path) -> dict:
    work = Path(work)
    if (work.exists() or work.is_symlink() or not work.parent.is_dir()
            or work.parent.is_symlink()):
        raise ValueError("Stage288 generated-only work root must be new")
    work.mkdir(mode=0o700)
    try:
        input_dir = work / "inputs"
        input_dir.mkdir(mode=0o700)
        for name, color in zip(SLOTS, COLORS):
            with (input_dir / name).open("xb") as dst:
                dst.write(generated_dds(color))
        output = work / "staged"
        summary = stage286_prepare(input_dir, shaders, output)
        if (summary["material_slots_accepted"] != 3 or
                summary["ps3_resource_format_verified"] is not False or
                summary["original_foj_material_mapping_verified"] is not False or
                summary["physical_switch_gpu_verified"] is not False):
            raise ValueError("Stage288 source staging provenance mismatch")
        checked = stage286_verify(output)
        if checked != summary:
            raise ValueError("Stage288 generated-only local binding mismatch")
        _new_public_report(evidence, "generated-input.json", {
            "schema": SCHEMA,
            "scenario": "original",
            "source": "generated-only Stage286 local DDS bridge",
            "generated_only": True,
            "original_ps3_resources": False,
            "actual_gpu_verified": False,
            "private_binding_manifest_archived": False,
            "expected_native_sort": [2, 1, 0],
            "expected_dds_sha256": expected_hashes(),
        })
        return summary
    except BaseException:
        # This function exclusively creates a brand-new synthetic work root.
        shutil.rmtree(work)
        raise


def attest(work: Path, evidence: Path, phase: str) -> dict:
    if phase not in ("before", "after"):
        raise ValueError("Stage288 invalid DDS observation phase")
    root = Path(work) / "staged"
    summary = stage286_verify(root)
    if summary["material_slots_accepted"] != 3:
        raise ValueError("Stage288 incorrect staged slot count")
    slots = root / SUBDIR
    for name, color in zip(SLOTS, COLORS):
        path = slots / name
        if path.is_symlink() or not path.is_file() or path.read_bytes() != generated_dds(color):
            raise ValueError("Stage288 DDS is no longer canonical public synthetic input")
    receipt = {
        "schema": SCHEMA,
        "phase": phase,
        "generated_only": True,
        "original_ps3_resources": False,
        "private_binding_manifest_archived": False,
        "material_slots_verified": 3,
        "dds_sha256": expected_hashes(),
    }
    _new_public_report(Path(evidence), f"dds-{phase}.json", receipt)
    return receipt


def audit(evidence: Path) -> dict:
    evidence = Path(evidence)
    origin = json.loads((evidence / "generated-input.json").read_text(encoding="utf-8"))
    if origin != {
        "schema": SCHEMA,
        "scenario": "original",
        "source": "generated-only Stage286 local DDS bridge",
        "generated_only": True,
        "original_ps3_resources": False,
        "actual_gpu_verified": False,
        "private_binding_manifest_archived": False,
        "expected_native_sort": [2, 1, 0],
        "expected_dds_sha256": expected_hashes(),
    }:
        raise ValueError("Stage288 generated input provenance mismatch")
    for phase in ("before", "after"):
        seen = json.loads((evidence / f"dds-{phase}.json").read_text(encoding="utf-8"))
        if seen != {
            "schema": SCHEMA,
            "phase": phase,
            "generated_only": True,
            "original_ps3_resources": False,
            "private_binding_manifest_archived": False,
            "material_slots_verified": 3,
            "dds_sha256": expected_hashes(),
        }:
            raise ValueError("Stage288 actual staged DDS observation mismatch")
    markers = {
        "native-sort-pass.txt": b"FOJ_NATIVE_SORT_V1 2,1,0\n",
        "native-alpha-pass.txt": expected_receipt("original"),
    }
    for filename, expected in markers.items():
        path = evidence / filename
        if path.is_symlink() or not path.is_file() or path.read_bytes() != expected:
            raise ValueError("Stage288 missing or invalid native guest receipt")
    for forbidden in ("native-rear-alpha-reject.txt", "native-topology-reject.txt", MANIFEST):
        path = evidence / forbidden
        if path.exists() or path.is_symlink():
            raise ValueError("Stage288 contradictory guest evidence or private manifest leak")
    first_path, later_path = (evidence / name for name in FRAMES)
    if any(path.is_symlink() or not path.is_file() for path in (first_path, later_path)):
        raise ValueError("Stage288 guest frames missing or linked")
    first, second = inspect(first_path, "original"), inspect(later_path, "original")
    with Image.open(first_path) as a, Image.open(later_path) as b:
        x, y = a.convert("RGB"), b.convert("RGB")
    if ImageChops.difference(x, y).getbbox() is None:
        raise ValueError("Stage288 duplicate guest frame")
    if sum(x.getpixel(p) != y.getpixel(p) for p in BACKGROUNDS) < 3:
        raise ValueError("Stage288 GPU clear-color phase unchanged")
    if any(first[n]["matching_pixels"] != second[n]["matching_pixels"] for n in first):
        raise ValueError("Stage288 changed GPU material footprint")
    return {
        "schema": "foj.stage288.actual_guest_three_dds_binding.v1",
        "generated_only": True,
        "original_ps3_resources": False,
        "physical_switch_verified": False,
        "source": SCHEMA,
        "verified_guest_frames": 2,
        "material_slots": 3,
        "canonical_dds_before_after_checked": True,
        "native_sort_and_pass_receipts_checked": True,
        "background_clear_phase_changed": True,
        "first": first,
        "later": second,
        "warning": "Generated SD bridge and synthetic materials only; original game assets not checked.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    p = commands.add_parser("prepare")
    p.add_argument("--work-root", required=True, type=Path)
    p.add_argument("--shaders", required=True, type=Path)
    p.add_argument("--evidence", required=True, type=Path)
    a = commands.add_parser("attest")
    a.add_argument("--work-root", required=True, type=Path)
    a.add_argument("--evidence", required=True, type=Path)
    a.add_argument("--phase", choices=("before", "after"), required=True)
    v = commands.add_parser("audit")
    v.add_argument("--evidence", required=True, type=Path)
    v.add_argument("--report", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = prepare(args.work_root, args.shaders, args.evidence)
        elif args.action == "attest":
            result = attest(args.work_root, args.evidence, args.phase)
        else:
            result = audit(args.evidence)
            _new_public_report(args.evidence, args.report.name, result)
    except (OSError, ValueError, KeyError, TypeError):
        print("Stage288 generated-only GPU bridge refused; inspect CI locally.",
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
