"""Generated-only stage-178 tests: no physical Nintendo Switch evidence."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools.foj_stage165_sd_bundle import INPUTS, publish_bundle
from tools.foj_stage171_build_identity import build_receipt, write_receipt
from tools.foj_stage178_sd_copy_preflight import audit_sd_copy

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "c" * 40
RUN = 39081111127


def nro(marker: int) -> bytes:
    result = bytearray(128)
    result[16:20] = b"NRO0"
    struct.pack_into("<I", result, 24, 128)
    result[-1] = marker
    return bytes(result)


def dksh(kind: str, marker: int) -> bytes:
    result = bytearray(512)
    struct.pack_into("<6I", result, 0, 0x48534B44, 24, 256, 256, 24, 1)
    struct.pack_into("<6I", result, 24, 0 if kind == "vertex" else 1,
                     0, 0, 0, 0, 0)
    result[-1] = marker
    return bytes(result)


class Stage178SDCopyTests(unittest.TestCase):
    def prepare(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        built = root / "buildroot"
        sd_root = root / "sd-root"
        sd_root.mkdir()
        for index, (relative, _, kind) in enumerate(INPUTS):
            target = built / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(nro(index + 1) if kind == "nro"
                               else dksh(kind, index + 1))
        archive = root / "bundle.zip"
        publish_bundle(built, archive)
        receipt = build_receipt(archive, COMMIT, RUN)
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if not name.startswith("switch/foj/"):
                    continue
                destination = sd_root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(z.read(name))
        return tmp, sd_root, archive, receipt

    @staticmethod
    def audit(root, bundle, receipt, commit=COMMIT, run=RUN):
        return audit_sd_copy(root, bundle, receipt, commit, run)

    def test_six_fixed_files_match_without_hardware_attestation(self):
        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            (sd / "unrelated-not-project.txt").write_text("safe other content")
            (sd / "switch/other-homebrew").mkdir()
            result = self.audit(sd, bundle, receipt)
            self.assertEqual(result["sd_copy_files_checked"], 6)
            self.assertTrue(result["sd_copy_matches"])
            self.assertEqual(len(result["files"]), 6)
            self.assertFalse(result["physical_switch_execution_verified"])
            self.assertFalse(result["gpu_scanout_verified"])
            self.assertFalse(result["original_foj_assets_verified"])
            self.assertFalse(result["gameplay_verified"])
            self.assertNotIn(str(sd), json.dumps(result))

    def test_wrong_commit_run_or_receipt_rejected(self):
        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            for c, n in (("d" * 40, RUN), (COMMIT, RUN + 1)):
                with self.subTest(commit=c, run=n):
                    with self.assertRaises(ValueError):
                        self.audit(sd, bundle, receipt, c, n)
            bad = dict(receipt, bundle_sha256="f" * 64)
            with self.assertRaises(ValueError):
                self.audit(sd, bundle, bad)

    def test_missing_and_extra_file_rejected(self):
        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            p = sd / "switch/foj/gpu/material0.dds"
            p.unlink()
            with self.assertRaises(ValueError):
                self.audit(sd, bundle, receipt)
            p.write_bytes(b"not valid")
            with self.assertRaises(ValueError):
                self.audit(sd, bundle, receipt)

    def test_extra_file_in_project_directory_rejected(self):
        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            path = sd / "switch/foj/unknown-private.bin"
            path.write_bytes(b"unexpected")
            with self.assertRaises(ValueError):
                self.audit(sd, bundle, receipt)

    def test_modified_but_structurally_valid_nro_rejected(self):
        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            path = sd / "switch/foj/foj-deko3d-triangle-research.nro"
            data = bytearray(path.read_bytes())
            data[-1] ^= 7
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                self.audit(sd, bundle, receipt)

    def test_modified_synthetic_dds_rejected(self):
        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            path = sd / "switch/foj/gpu/material1.dds"
            data = bytearray(path.read_bytes())
            data[-1] ^= 7
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                self.audit(sd, bundle, receipt)

    def test_symlinked_source_and_directory_rejected(self):
        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            path = sd / "switch/foj/gpu/foj_actor.vert.dksh"
            original = sd / "switch/foj/gpu/actor.bak"
            path.rename(original)
            path.symlink_to(original)
            with self.assertRaises(ValueError):
                self.audit(sd, bundle, receipt)

        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            path = sd / "switch/foj/gpu"
            other = sd / "switch/foj/real_gpu"
            path.rename(other)
            path.symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.audit(sd, bundle, receipt)

    def test_cli_read_only_and_private_path_not_reported(self):
        tmp, sd, bundle, receipt = self.prepare()
        with tmp:
            receipt_file = sd.parent / "build-receipt.json"
            # Existing receipt is validated but is never overwritten.
            write_receipt(bundle, receipt_file, COMMIT, RUN)
            saved = receipt_file.read_bytes()
            command = [
                sys.executable, "-m", "tools.foj_stage178_sd_copy_preflight",
                "--sd-root", str(sd), "--bundle", str(bundle),
                "--receipt", str(receipt_file),
                "--expected-commit", COMMIT, "--expected-run-id", str(RUN),
            ]
            good = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(json.loads(good.stdout)["sd_copy_files_checked"], 6)
            self.assertEqual(receipt_file.read_bytes(), saved)
            (sd / "switch/foj/gpu/material0.dds").unlink()
            failed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertNotIn(str(sd), failed.stderr)
            self.assertNotIn(str(sd), failed.stdout)


if __name__ == "__main__":
    unittest.main()
