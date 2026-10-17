"""Stage 174: generated-only native artifacts, never Switch hardware evidence."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stage165_sd_bundle import INPUTS, publish_bundle, ZIP_PREFIX
from tools.foj_stage171_build_identity import MEMBERS, build_receipt, write_receipt
from tools.foj_stage174_native_artifact_coherence import (
    SCHEMA, verify_native_outputs, write_gate,
)

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
RUN = 39079408807


def fake_nro(marker: int) -> bytes:
    payload = bytearray(128)
    payload[16:20] = b"NRO0"
    struct.pack_into("<I", payload, 24, len(payload))
    payload[60] = marker
    return bytes(payload)


def fake_shader(kind: str, marker: int) -> bytes:
    payload = bytearray(512)
    struct.pack_into("<6I", payload, 0, 0x48534B44, 24, 256, 256, 24, 1)
    struct.pack_into("<6I", payload, 24, 0 if kind == "vertex" else 1, 0, 0, 0, 0, 0)
    payload[-1] = marker
    return bytes(payload)


class NativeArtifactCoherenceTests(unittest.TestCase):
    def prepare(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        for idx, (relative, _, kind) in enumerate(INPUTS):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                fake_nro(idx + 1) if kind == "nro" else fake_shader(kind, idx + 1)
            )
        bundle = root / "generated.zip"
        publish_bundle(root, bundle)
        receipt = build_receipt(bundle, COMMIT, RUN)
        return tmp, root, bundle, receipt

    @staticmethod
    def check(root, bundle, receipt, commit=COMMIT, run=RUN):
        return verify_native_outputs(root, bundle, receipt, commit, run)

    def test_four_loose_files_match_fixed_zip_and_never_attest_hardware(self):
        tmp, root, bundle, receipt = self.prepare()
        with tmp:
            report = self.check(root, bundle, receipt)
            self.assertEqual(report["schema"], SCHEMA)
            self.assertTrue(report["loose_and_zip_consistent_at_check_time"])
            self.assertEqual(report["binary_count"], 4)
            self.assertEqual(
                [r["sd_relative_path"] for r in report["matching_binaries"]],
                list(MEMBERS),
            )
            self.assertTrue(all(r["matches_zip_receipt"]
                                for r in report["matching_binaries"]))
            self.assertFalse(report["switch_hardware_execution_verified"])
            self.assertFalse(report["gpu_scanout_verified"])
            self.assertFalse(report["original_foj_assets_verified"])
            self.assertFalse(report["gameplay_verified"])
            self.assertNotIn(str(root), json.dumps(report))

    def test_modified_loose_nro_rejected_even_if_nro_still_valid(self):
        tmp, root, bundle, receipt = self.prepare()
        with tmp:
            p = root / INPUTS[1][0]
            altered = bytearray(p.read_bytes())
            altered[60] ^= 7
            p.write_bytes(altered)
            with self.assertRaises(ValueError):
                self.check(root, bundle, receipt)

    def test_modified_loose_dksh_rejected_even_if_header_still_valid(self):
        tmp, root, bundle, receipt = self.prepare()
        with tmp:
            p = root / INPUTS[3][0]
            altered = bytearray(p.read_bytes())
            altered[-1] ^= 7
            p.write_bytes(altered)
            with self.assertRaises(ValueError):
                self.check(root, bundle, receipt)

    def test_wrong_ci_commit_run_or_receipt_hash_rejected(self):
        tmp, root, bundle, receipt = self.prepare()
        with tmp:
            for commit, run in (("b" * 40, RUN), (COMMIT, RUN + 1)):
                with self.subTest(commit=commit, run=run):
                    with self.assertRaises(ValueError):
                        self.check(root, bundle, receipt, commit, run)
            bad = dict(receipt, bundle_sha256="f" * 64)
            with self.assertRaises(ValueError):
                self.check(root, bundle, bad)

    def test_missing_or_symlinked_loose_output_rejected(self):
        tmp, root, bundle, receipt = self.prepare()
        with tmp:
            p = root / INPUTS[0][0]
            original = p.with_name("original.nro")
            p.rename(original)
            with self.assertRaises(ValueError):
                self.check(root, bundle, receipt)
            p.symlink_to(original)
            with self.assertRaises(ValueError):
                self.check(root, bundle, receipt)

    def test_symlinked_ancestor_directory_rejected(self):
        tmp, root, bundle, receipt = self.prepare()
        with tmp:
            folder = root / "gpu" / "build"
            relocated = root / "gpu" / "saved-build"
            folder.rename(relocated)
            folder.symlink_to(relocated, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.check(root, bundle, receipt)

    def test_exclusive_report_writer_does_not_overwrite_existing_file(self):
        tmp, root, bundle, receipt = self.prepare()
        with tmp:
            report = self.check(root, bundle, receipt)
            target = root / "coherence.json"
            write_gate(target, report)
            saved = target.read_bytes()
            self.assertEqual(json.loads(saved), report)
            with self.assertRaises(ValueError):
                write_gate(target, report)
            self.assertEqual(target.read_bytes(), saved)

    def test_cli_creates_gate_and_detects_modified_binary_without_output(self):
        tmp, root, bundle, receipt = self.prepare()
        with tmp:
            rec = root / "ci-receipt.json"
            write_receipt(bundle, rec, COMMIT, RUN)
            result = root / "native-coherence.json"
            cmd = [
                sys.executable, "-m", "tools.foj_stage174_native_artifact_coherence",
                "--repo-root", str(root), "--bundle", str(bundle),
                "--receipt", str(rec), "--expected-commit", COMMIT,
                "--expected-run-id", str(RUN), "--output", str(result),
            ]
            passed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertTrue(result.exists())
            self.assertNotIn(str(root), passed.stdout)
            self.assertFalse(json.loads(result.read_text())["gpu_scanout_verified"])
            result.unlink()
            p = root / INPUTS[2][0]
            blob = bytearray(p.read_bytes())
            blob[-1] ^= 3
            p.write_bytes(blob)
            failed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(result.exists())
            self.assertNotIn(str(root), failed.stderr)
            self.assertNotIn(str(root), failed.stdout)


if __name__ == "__main__":
    unittest.main()
