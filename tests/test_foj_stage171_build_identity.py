"""Stage 171: only generated-only build receipts and fabricated observations."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools.foj_stage165_sd_bundle import INPUTS, publish_bundle, ZIP_PREFIX
from tools.foj_stage166_hardware_observations import blank_template
from tools.foj_stage170_cpu_visual_alignment import LINK_BASIS, blank_link
from tools.foj_stage171_build_identity import (
    NRO, SCHEMA, bind, build_receipt, read_local_nro, read_receipt,
    validate_receipt, write_receipt,
)
from tools.foj_stage169_two_attempt_recovery import read_strict

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
RUN = 39073487218


def dummy_nro() -> bytes:
    blob = bytearray(128)
    blob[16:20] = b"NRO0"
    struct.pack_into("<I", blob, 24, len(blob))
    return bytes(blob)


def dummy_shader(kind: str) -> bytes:
    blob = bytearray(512)
    struct.pack_into("<6I", blob, 0, 0x48534B44, 24, 256, 256, 24, 1)
    struct.pack_into("<6I", blob, 24, 0 if kind == "vertex" else 1, 0, 0, 0, 0)
    return bytes(blob)


def fixture_tree(root: Path) -> None:
    for relative, _staged, kind in INPUTS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(dummy_nro() if kind == "nro" else dummy_shader(kind))


def cpu_line(slot, stage, event, frame=0):
    return (f"FOJBOOT1 slot={slot:02d} step={stage:02d} "
            f"event={event} frames={frame:010d}\n").encode()


def first_failure():
    return b"".join((
        cpu_line(0, 1, 1), cpu_line(0, 1, 2), cpu_line(0, 2, 1),
        cpu_line(0, 2, 3), cpu_line(0, 11, 4),
    ))


def second_cpu_success():
    rows = []
    for stage in range(1, 11):
        rows.extend((cpu_line(1, stage, 1),
                     cpu_line(1, stage, 2, 5 if stage == 10 else 0)))
    rows.append(cpu_line(1, 11, 4, 5))
    return b"".join(rows)


class Stage171ReceiptTests(unittest.TestCase):
    def prepare(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        fixture_tree(root)
        archive = root / "generated-research.zip"
        publish_bundle(root, archive)
        receipt = build_receipt(archive, COMMIT, RUN)
        sheet = blank_template()
        sheet["build"] = {
            "git_commit": COMMIT,
            "github_run_id": RUN,
            "sd_bundle_sha256": receipt["bundle_sha256"],
        }
        sheet["scenarios"][2]["observations"][0]["seen"] = "green"
        sheet["scenarios"][2]["observations"][1]["seen"] = "green"
        sheet["scenarios"][2]["observations"][2]["seen"] = "two_checkerboards"
        link = dict(blank_link(), boot_slot=1, visual_scenario="C",
                    association_basis=LINK_BASIS)
        earlier = root / "foj-boot-00.txt"
        later = root / "foj-boot-01.txt"
        earlier.write_bytes(first_failure())
        later.write_bytes(second_cpu_success())
        return tmp, root, archive, receipt, sheet, link, earlier, later

    @staticmethod
    def compare(archive, receipt, sheet, link, earlier, later, sd_nro=None):
        return bind(archive, receipt, sheet, read_strict(earlier),
                    read_strict(later), link, sd_nro)

    def test_complete_generated_evidence_is_never_hardware_attestation(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            result = self.compare(z, r, sheet, link, a, b)
            self.assertTrue(result["artifact_bundle_verified"])
            self.assertTrue(result["receipt_matches_research_archive"])
            self.assertEqual(result["operator_build_metadata_status"],
                             "operator_recorded_build_identity_matches_receipt")
            self.assertEqual(result["operator_declared_build_fields"], 3)
            self.assertEqual(result["overall_interpretation"],
                             "operator_build_and_visual_claims_consistent_but_unverified")
            self.assertFalse(result["gpu_scanout_verified"])
            self.assertFalse(result["hardware_execution_verified"])
            self.assertFalse(result["switch_gameplay_verified"])
            self.assertFalse(result["sd_nro_copy_compared"])
            self.assertNotIn(str(root), json.dumps(result))
            self.assertNotIn(COMMIT, json.dumps(result))

    def test_blank_build_metadata_stays_explicitly_unbound(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            sheet["build"] = {name: None for name in sheet["build"]}
            result = self.compare(z, r, sheet, link, a, b)
            self.assertEqual(result["operator_build_metadata_status"],
                             "operator_build_metadata_missing")
            self.assertEqual(result["overall_interpretation"],
                             "incomplete_or_unconfirmed_manual_test_evidence")
            self.assertFalse(result["hardware_execution_verified"])

    def test_partial_correct_metadata_never_counts_as_full_build_binding(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            sheet["build"]["github_run_id"] = None
            result = self.compare(z, r, sheet, link, a, b)
            self.assertEqual(result["operator_declared_build_fields"], 2)
            self.assertEqual(result["operator_build_metadata_status"],
                             "operator_build_metadata_incomplete")

    def test_reject_cross_build_commit_run_and_zip_digest(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            for field, wrong in (
                ("git_commit", "f" * 40),
                ("github_run_id", RUN + 1),
                ("sd_bundle_sha256", "f" * 64),
            ):
                with self.subTest(field=field):
                    local = json.loads(json.dumps(sheet))
                    local["build"][field] = wrong
                    with self.assertRaises(ValueError):
                        self.compare(z, r, local, link, a, b)

    def test_receipt_binary_digest_swap_and_shape_rejected(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            broken = json.loads(json.dumps(r))
            broken["built_members"][1]["sha256"] = "f" * 64
            with self.assertRaises(ValueError):
                self.compare(z, broken, sheet, link, a, b)
            for update in (
                lambda v: v.update(extra=1),
                lambda v: v["built_members"].reverse(),
                lambda v: v.update(switch_hardware_verified=True),
                lambda v: v.update(git_commit=True),
                lambda v: v.update(github_run_id="1234"),
                lambda v: v.update(bundle_sha256="not_a_digest"),
                lambda v: v["built_members"].append(v["built_members"][0]),
            ):
                case = json.loads(json.dumps(r))
                update(case)
                with self.assertRaises(ValueError):
                    validate_receipt(case)

    def test_validated_archive_repacked_with_altered_nro_not_interchangeable(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            with zipfile.ZipFile(z) as original:
                parts = {n: original.read(n) for n in original.namelist()}
            mutated = bytearray(parts[NRO])
            mutated[60] ^= 1  # within fabricated NRO, still structurally valid
            parts[NRO] = bytes(mutated)
            # Stage165 internal digest must be recomputed: otherwise
            # stage166 archive validation must fail closed even sooner.
            different = root / "different-research.zip"
            with zipfile.ZipFile(different, "w") as out:
                for path, payload in parts.items():
                    out.writestr(path, payload)
            with self.assertRaises(ValueError):
                self.compare(different, r, sheet, link, a, b)

    def test_sd_copy_matches_only_when_nro_bytes_match(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            sd_dir = root / "sd"
            sd_dir.mkdir()
            copied = sd_dir / "foj-deko3d-triangle-research.nro"
            copied.write_bytes(dummy_nro())
            report = self.compare(z, r, sheet, link, a, b, copied)
            self.assertTrue(report["sd_nro_copy_compared"])
            self.assertTrue(report["sd_nro_copy_matches_generated_archive"])
            self.assertFalse(report["hardware_execution_verified"])
            mutated = bytearray(dummy_nro())
            mutated[-1] = 17
            copied.write_bytes(mutated)
            with self.assertRaises(ValueError):
                self.compare(z, r, sheet, link, a, b, copied)

    def test_sd_nro_symlink_wrong_filename_and_missing_rejected(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            sd = root / "sd"
            sd.mkdir()
            src = sd / "file.nro"
            src.write_bytes(dummy_nro())
            linkpath = sd / "foj-deko3d-triangle-research.nro"
            linkpath.symlink_to(src)
            with self.assertRaises(ValueError):
                read_local_nro(linkpath)
            with self.assertRaises(ValueError):
                read_local_nro(src)
            linkpath.unlink()
            with self.assertRaises(ValueError):
                read_local_nro(linkpath)

    def test_exclusive_receipt_and_duplicate_json_keys_rejected(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            receipt = root / "receipt.json"
            write_receipt(z, receipt, COMMIT, RUN)
            self.assertEqual(read_receipt(receipt), r)
            baseline = receipt.read_bytes()
            with self.assertRaisesRegex(ValueError, "NEW"):
                write_receipt(z, receipt, COMMIT, RUN)
            self.assertEqual(receipt.read_bytes(), baseline)
            receipt.write_text('{"schema":1,"schema":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_receipt(receipt)
            receipt.write_bytes(b"X" * 4097)
            with self.assertRaises(ValueError):
                read_receipt(receipt)

    def test_receipt_symlink_rejected(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            valid = root / "receipt-valid.json"
            valid.write_text(json.dumps(r), encoding="utf-8")
            alias = root / "receipt-alias.json"
            alias.symlink_to(valid)
            with self.assertRaises(ValueError):
                read_receipt(alias)

    def test_cli_receipt_generation_and_matching_manual_claim(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            receipt = root / "receipt.json"
            ledger = root / "private-observations.json"
            association = root / "private-link.json"
            ledger.write_text(json.dumps(sheet), encoding="utf-8")
            association.write_text(json.dumps(link), encoding="utf-8")
            init = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage171_build_identity",
                 "--bundle", str(z), "--create-receipt", str(receipt),
                 "--git-commit", COMMIT, "--run-id", str(RUN)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertNotIn(str(root), init.stdout)
            result = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage171_build_identity",
                 "--bundle", str(z), "--receipt", str(receipt),
                 "--ledger", str(ledger), "--before", str(a),
                 "--after", str(b), "--link", str(association)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            info = json.loads(result.stdout)
            self.assertFalse(info["hardware_execution_verified"])
            self.assertEqual(info["operator_declared_build_fields"], 3)
            self.assertNotIn(str(root), result.stdout)

    def test_cli_invalid_data_never_prints_private_location(self):
        tmp, root, z, r, sheet, link, a, b = self.prepare()
        with tmp:
            receipt = root / "receipt.json"
            receipt.write_text(json.dumps(r), encoding="utf-8")
            ledger = root / "private-observations.json"
            ledger.write_text(json.dumps(sheet), encoding="utf-8")
            badlink = root / "link.json"
            badlink.write_text('{"source":"/private/game/asset.bin"}', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage171_build_identity",
                 "--bundle", str(z), "--receipt", str(receipt),
                 "--ledger", str(ledger), "--before", str(a),
                 "--after", str(b), "--link", str(badlink)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn(str(root), proc.stderr)
            self.assertNotIn("asset.bin", proc.stderr)


if __name__ == "__main__":
    unittest.main()
