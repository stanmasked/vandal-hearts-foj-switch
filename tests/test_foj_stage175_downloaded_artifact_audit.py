"""Stage 175 uses only fabricated NRO/DKSH bytes, not real Switch captures."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stage165_sd_bundle import INPUTS, publish_bundle
from tools.foj_stage166_hardware_observations import blank_template
from tools.foj_stage171_build_identity import write_receipt
from tools.foj_stage174_native_artifact_coherence import (
    verify_native_outputs, write_gate,
)
from tools.foj_stage175_downloaded_artifact_audit import (
    EXTRA, SCHEMA, STAGE174, STAGE175, create_receipt, verify_download,
)

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
RUN = 39079408807


def fake_nro(marker):
    payload = bytearray(128)
    payload[16:20] = b"NRO0"
    struct.pack_into("<I", payload, 24, 128)
    payload[-1] = marker
    return bytes(payload)


def fake_dksh(kind, marker):
    payload = bytearray(512)
    struct.pack_into("<6I", payload, 0, 0x48534B44, 24, 256, 256, 24, 1)
    struct.pack_into("<6I", payload, 24, 0 if kind == "vertex" else 1, 0, 0, 0, 0)
    payload[-1] = marker
    return bytes(payload)


class Stage175DownloadedArtifactTests(unittest.TestCase):
    def prepare(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for index, (path, _staged, kind) in enumerate(INPUTS):
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                fake_nro(index + 1) if kind == "nro"
                else fake_dksh(kind, index + 1)
            )
        fifth = root / EXTRA[0]
        fifth.write_bytes(fake_dksh("fragment", 5))
        bundle = root / "build/foj-stage165-gpu-sd-smoke.zip"
        publish_bundle(root, bundle)
        receipt = root / "build/foj-stage171-ci-build-receipt.json"
        write_receipt(bundle, receipt, COMMIT, RUN)
        from tools.foj_stage171_build_identity import read_receipt
        coherence = verify_native_outputs(root, bundle, read_receipt(receipt),
                                          COMMIT, RUN)
        write_gate(root / STAGE174, coherence)
        (root / "build/foj-stage166-blank-observations.json").write_text(
            json.dumps(blank_template()), encoding="utf-8"
        )
        create_receipt(root, COMMIT, RUN)
        return temp, root

    def test_valid_downloaded_inventory_and_all_five_hashes(self):
        temp, root = self.prepare()
        with temp:
            verify_download(root, COMMIT, RUN)
            result = json.loads((root / STAGE175).read_text())
            self.assertEqual(result["schema"], SCHEMA)
            self.assertEqual(result["published_binary_count"], 5)
            self.assertEqual(len(result["published_binaries"]), 5)
            self.assertEqual(result["published_binaries"][-1]["published_relative_path"],
                             EXTRA[0])
            self.assertTrue(result["stage174_zip_consistency_rechecked"])
            for field in ("physical_switch_execution_verified", "gpu_scanout_verified",
                          "original_foj_assets_verified", "gameplay_verified"):
                self.assertIs(result[field], False)
            self.assertNotIn(str(root), json.dumps(result))

    def test_fifth_shader_tampered_after_receipt_rejected(self):
        temp, root = self.prepare()
        with temp:
            path = root / EXTRA[0]
            blob = bytearray(path.read_bytes())
            blob[-1] ^= 15
            path.write_bytes(blob)
            with self.assertRaises(ValueError):
                verify_download(root, COMMIT, RUN)

    def test_fifth_shader_symlink_and_missing_rejected(self):
        temp, root = self.prepare()
        with temp:
            path = root / EXTRA[0]
            target = path.with_suffix(".saved")
            path.rename(target)
            with self.assertRaises(ValueError):
                verify_download(root, COMMIT, RUN)
            path.symlink_to(target)
            with self.assertRaises(ValueError):
                verify_download(root, COMMIT, RUN)

    def test_stage174_coherence_report_tamper_rejected(self):
        temp, root = self.prepare()
        with temp:
            path = root / STAGE174
            data = json.loads(path.read_text())
            data["loose_and_zip_consistent_at_check_time"] = False
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_download(root, COMMIT, RUN)

    def test_stage175_manifest_forged_digest_rejected(self):
        temp, root = self.prepare()
        with temp:
            path = root / STAGE175
            data = json.loads(path.read_text())
            data["published_binaries"][-1]["sha256"] = "f" * 64
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_download(root, COMMIT, RUN)

    def test_stage175_receipt_duplicate_json_keys_rejected(self):
        temp, root = self.prepare()
        with temp:
            (root / STAGE175).write_text('{"schema":1,"schema":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_download(root, COMMIT, RUN)

    def test_wrong_run_or_commit_rejected(self):
        temp, root = self.prepare()
        with temp:
            for commit, run in (("f" * 40, RUN), (COMMIT, RUN + 1)):
                with self.subTest(commit=commit, run=run):
                    with self.assertRaises(ValueError):
                        verify_download(root, commit, run)

    def test_unexpected_file_and_symlink_directory_rejected(self):
        temp, root = self.prepare()
        with temp:
            extra = root / "unlisted-private.txt"
            extra.write_bytes(b"x")
            with self.assertRaises(ValueError):
                verify_download(root, COMMIT, RUN)
            extra.unlink()
            directory = root / "gpu/build"
            saved = root / "gpu/saved"
            directory.rename(saved)
            directory.symlink_to(saved, target_is_directory=True)
            with self.assertRaises(ValueError):
                verify_download(root, COMMIT, RUN)

    def test_existing_stage175_manifest_cannot_be_overwritten(self):
        temp, root = self.prepare()
        with temp:
            path = root / STAGE175
            initial = path.read_bytes()
            with self.assertRaises(ValueError):
                create_receipt(root, COMMIT, RUN)
            self.assertEqual(path.read_bytes(), initial)

    def test_command_line_pre_publish_then_post_download_audit(self):
        temp, root = self.prepare()
        with temp:
            (root / STAGE175).unlink()
            command = [
                sys.executable, "-m", "tools.foj_stage175_downloaded_artifact_audit",
                "--artifact-root", str(root), "--expected-commit", COMMIT,
                "--expected-run-id", str(RUN),
            ]
            create = subprocess.run(command + ["--create-receipt"], cwd=ROOT,
                                    text=True, capture_output=True)
            self.assertEqual(create.returncode, 0, create.stderr)
            verify = subprocess.run(command + ["--verify-downloaded"], cwd=ROOT,
                                    text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertNotIn(str(root), verify.stdout)
            (root / EXTRA[0]).write_bytes(b"garbled")
            failure = subprocess.run(command + ["--verify-downloaded"], cwd=ROOT,
                                     text=True, capture_output=True)
            self.assertNotEqual(failure.returncode, 0)
            self.assertNotIn(str(root), failure.stderr)


if __name__ == "__main__":
    unittest.main()
