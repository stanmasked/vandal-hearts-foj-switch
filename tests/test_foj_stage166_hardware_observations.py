"""Generated-only tests for private/manual stage-166 Switch observations.

All positive on-screen observations are deliberately TEST FIXTURES, not actual
console observations. Never upload completed local ledgers as CI artifacts.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools.foj_stage165_sd_bundle import INPUTS, publish_bundle
from tools.foj_stage166_hardware_observations import (
    SCENARIOS, audit, blank_template, inspect_bundle, read_ledger, write_template,
)

FAKE_COMMIT = "a" * 40


def fake_nro() -> bytes:
    blob = bytearray(128)
    blob[16:20] = b"NRO0"
    struct.pack_into("<I", blob, 24, 128)
    return bytes(blob)


def fake_dksh(kind: str) -> bytes:
    blob = bytearray(512)
    struct.pack_into("<6I", blob, 0, 0x48534B44, 24, 256, 256, 24, 1)
    struct.pack_into("<6I", blob, 24, 0 if kind == "vertex" else 1, 0, 0, 0, 0, 0)
    return bytes(blob)


def fake_build(root: Path):
    for relative, _staged, kind in INPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fake_nro() if kind == "nro" else fake_dksh(kind))


def fill_scenarios(report):
    for entry in report["scenarios"]:
        for item, appearance in zip(entry["observations"],
                                    SCENARIOS[entry["id"]]):
            item["seen"] = appearance


def fill_metadata(report, digest="b" * 64):
    report["build"] = {
        "git_commit": FAKE_COMMIT,
        "github_run_id": 39068392320,
        "sd_bundle_sha256": digest,
    }
    report["hardware"] = {
        "model": "oled",
        "homebrew_mode": "homebrew_menu_title",
        "local_test_date": "2026-10-17",
    }


class Stage166ObservationLedgerTests(unittest.TestCase):
    def test_blank_template_records_zero_claimed_observations(self):
        doc = blank_template()
        self.assertEqual(len(doc["scenarios"]), 5)
        self.assertEqual([s["id"] for s in doc["scenarios"]], list(SCENARIOS))
        res = audit(doc)
        self.assertEqual(res["declared_screen_stages"], 0)
        self.assertFalse(res["environment_metadata_complete"])
        self.assertFalse(res["hardware_execution_verified"])
        self.assertEqual([x["comparison"] for x in res["scenarios"]],
                         ["not_observed"] * 5)
        self.assertNotIn("matches_expected", json.dumps(res))

    def test_complete_synthetic_filled_fixture_never_claims_hardware_verified(self):
        doc = blank_template()
        fill_metadata(doc)
        fill_scenarios(doc)
        result = audit(doc)
        self.assertEqual(result["declared_screen_stages"], 15)
        self.assertTrue(result["environment_metadata_complete"])
        self.assertEqual([x["comparison"] for x in result["scenarios"]],
                         ["matches_expected"] * 5)
        self.assertFalse(result["hardware_execution_verified"])
        self.assertEqual(result["evidence_level"],
                         "operator-declared-only; no automatic hardware attestation")
        self.assertNotIn("oled", json.dumps(result))
        self.assertNotIn(FAKE_COMMIT, json.dumps(result))

    def test_incomplete_and_unexpected_screen_results_stay_visible(self):
        doc = blank_template()
        doc["scenarios"][0]["observations"][0]["seen"] = "blue"
        doc["scenarios"][3]["observations"][0]["seen"] = "green"
        doc["scenarios"][3]["observations"][1]["seen"] = "green"
        doc["scenarios"][3]["observations"][2]["seen"] = "two_checkerboards"
        result = audit(doc)
        self.assertEqual(result["declared_screen_stages"], 4)
        self.assertEqual(result["scenarios"][0]["comparison"], "incomplete")
        self.assertEqual(result["scenarios"][3]["comparison"],
                         "differs_from_expected")
        self.assertFalse(result["hardware_execution_verified"])

    def test_observation_hash_is_optional_but_requires_an_observation(self):
        doc = blank_template()
        row = doc["scenarios"][0]["observations"][0]
        row["capture_sha256"] = "c" * 64
        with self.assertRaises(ValueError):
            audit(doc)
        row["seen"] = "blue"
        self.assertEqual(audit(doc)["declared_capture_hashes"], 1)
        row["capture_sha256"] = "NOT-A-SHA"
        with self.assertRaises(ValueError):
            audit(doc)

    def test_unknown_keys_duplicate_rows_and_wrong_types_fail_closed(self):
        changes = [
            lambda d: d.update({"screenshot_path": "/secret/user.png"}),
            lambda d: d["scenarios"].reverse(),
            lambda d: d["scenarios"][0]["observations"][0].update({"unknown": 1}),
            lambda d: d["scenarios"][0]["observations"][0].update({"seen": True}),
            lambda d: d["scenarios"][0]["observations"][1].update({"stage": "slot0"}),
            lambda d: d["build"].update({"github_run_id": True}),
            lambda d: d["hardware"].update({"model": "/private/switch"}),
            lambda d: d["hardware"].update({"local_test_date": "2026-02-30"}),
        ]
        for index, modify in enumerate(changes):
            with self.subTest(index=index):
                doc = blank_template()
                modify(doc)
                with self.assertRaises(ValueError):
                    audit(doc)

    def test_template_exclusive_and_read_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.json"
            write_template(path)
            first = path.read_bytes()
            self.assertEqual(read_ledger(path), blank_template())
            with self.assertRaisesRegex(ValueError, "NEW"):
                write_template(path)
            self.assertEqual(path.read_bytes(), first)
            path.write_text('{"schema":1,"schema":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_ledger(path)
            path.write_bytes(b"x" * (64 * 1024 + 1))
            with self.assertRaises(ValueError):
                read_ledger(path)

    def test_structurally_valid_zip_and_ledger_digest_bind(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fixture"
            fake_build(root)
            archive = Path(tmp) / "bundle.zip"
            publish_bundle(root, archive)
            digest = inspect_bundle(archive)
            self.assertTrue(re.fullmatch("[0-9a-f]{64}", digest))
            doc = blank_template()
            fill_metadata(doc, digest)
            self.assertTrue(audit(doc, bundle_sha256=digest)
                            ["locally_supplied_bundle_hash_matched"])
            with self.assertRaisesRegex(ValueError, "digest"):
                audit(doc, bundle_sha256="d" * 64)

    def test_zip_checksum_corruption_rejected_even_with_valid_zip_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fixture"
            fake_build(root)
            good = Path(tmp) / "good.zip"
            publish_bundle(root, good)
            with zipfile.ZipFile(good, "r") as source:
                parts = {name: source.read(name) for name in source.namelist()}
            # Re-pack an altered stage165 entry, keeping a valid central dir.
            parts["switch/foj/gpu/material0.dds"] = (
                parts["switch/foj/gpu/material0.dds"][:-1] + b"\xfe")
            damaged = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(damaged, "w", compression=zipfile.ZIP_STORED) as z:
                for name, value in parts.items():
                    z.writestr(name, value)
            with self.assertRaises(ValueError):
                inspect_bundle(damaged)

    def test_unexpected_zip_member_and_duplicate_zip_name_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fixture"
            fake_build(root)
            good = Path(tmp) / "good.zip"
            publish_bundle(root, good)
            with zipfile.ZipFile(good) as src:
                parts = [(name, src.read(name)) for name in src.namelist()]
            for name, value in (
                ("unexpected", b"SECRET-PROPRIETARY"),
                (parts[0][0], parts[0][1]),
            ):
                outfile = Path(tmp) / f"bad-{len(name)}-{len(value)}.zip"
                with zipfile.ZipFile(outfile, "w") as out:
                    for srcname, srcvalue in parts:
                        out.writestr(srcname, srcvalue)
                    out.writestr(name, value)
                with self.assertRaises(ValueError):
                    inspect_bundle(outfile)

    def test_cli_never_leaks_local_paths_or_invents_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private-observations.json"
            init = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage166_hardware_observations",
                 "--init", str(path)], capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertIn("BLANK", init.stdout)
            self.assertNotIn(str(tmp), init.stdout)
            audit_result = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage166_hardware_observations",
                 "--audit", str(path)], capture_output=True, text=True)
            self.assertEqual(audit_result.returncode, 0, audit_result.stderr)
            self.assertFalse(json.loads(audit_result.stdout)
                             ["hardware_execution_verified"])
            self.assertNotIn(str(tmp), audit_result.stdout)

    def test_synthetic_fixture_with_bundle_cli_is_never_considered_attested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fixture"
            fake_build(root)
            archive = Path(tmp) / "archive.zip"
            publish_bundle(root, archive)
            ledger = Path(tmp) / "ledger.json"
            doc = blank_template()
            fill_scenarios(doc)
            fill_metadata(doc, inspect_bundle(archive))
            ledger.write_text(json.dumps(doc), encoding="utf-8")
            run = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage166_hardware_observations",
                 "--audit", str(ledger), "--bundle", str(archive)],
                capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertTrue(result["locally_supplied_bundle_hash_matched"])
            self.assertFalse(result["hardware_execution_verified"])
            self.assertEqual(result["declared_screen_stages"], 15)


if __name__ == "__main__":
    unittest.main()
