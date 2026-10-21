"""Stage289 publication gates: host fixtures are NEVER guest proof."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from test_stage288_generated_bridge_gpu import create_mock_evidence
from tools.foj_stage288_generated_bridge_gpu import audit
from tools.foj_stage289_public_guest_evidence import (
    PUBLIC_BRIDGE_FILES, ARCHIVE_HASH, RECEIPT, publish,
)


class VerifiedGuestEvidenceExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "runtime-evidence"
        self.source.mkdir()
        self.bridge = self.source / "bridge"
        create_mock_evidence(self.bridge)
        (self.bridge / "guest.log").write_text("generated NeXium test log\n")
        (self.source / ARCHIVE_HASH).write_text("a" * 64 + "  /tmp/nexium.tar.gz\n")
        (self.bridge / RECEIPT).write_text(json.dumps(audit(self.bridge)))
        self.output = root / "public"

    def test_exact_nine_public_files_without_raw_guest_log(self):
        report = publish(self.source, self.output)
        self.assertEqual(report["public_files"], 9)
        self.assertEqual(report["neixum_guest_frames_audited"], 2)
        self.assertFalse(report["raw_guest_log_uploaded"])
        self.assertFalse(report["original_ps3_resources"])
        self.assertTrue((self.output / "bridge" / "gpu-initial.png").is_file())
        self.assertTrue((self.output / ARCHIVE_HASH).is_file())
        self.assertEqual(len(tuple((self.output / "bridge").iterdir())),
                         len(PUBLIC_BRIDGE_FILES))
        self.assertFalse((self.output / "bridge" / "guest.log").exists())
        self.assertEqual(audit(self.output / "bridge"), audit(self.bridge))

    def test_unexpected_private_dds_never_published(self):
        (self.bridge / "sensitive.dds").write_bytes(b"not public")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            publish(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_unexpected_nested_private_directory_never_published(self):
        private = self.bridge / "private"
        private.mkdir()
        (private / "game.pkg").write_bytes(b"test")
        with self.assertRaisesRegex(ValueError, "unexpected evidence directory"):
            publish(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_symlinked_guest_frame_rejected(self):
        a = self.bridge / "gpu-initial.png"
        b = self.bridge / "gpu-later.png"
        a.unlink()
        a.symlink_to(b.name)
        with self.assertRaisesRegex(ValueError, "symlink"):
            publish(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_symlinked_source_root_rejected(self):
        alias = self.source.parent / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "fresh publication root"):
            publish(alias, self.output)

    def test_unexpected_original_stage286_private_manifest_rejected(self):
        (self.bridge / "owner-private-stage286-binding.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            publish(self.source, self.output)

    def test_tampered_stage288_receipt_rejected(self):
        p = self.bridge / RECEIPT
        content = json.loads(p.read_text())
        content["verified_guest_frames"] = 3
        p.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, "differs"):
            publish(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_tampered_before_dds_observation_rejected(self):
        p = self.bridge / "dds-before.json"
        content = json.loads(p.read_text())
        content["dds_sha256"]["material0.dds"] = "0" * 64
        p.write_text(json.dumps(content))
        with self.assertRaisesRegex(ValueError, "DDS observation mismatch"):
            publish(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_bad_archive_provenance_rejected(self):
        (self.source / ARCHIVE_HASH).write_text("untrusted")
        with self.assertRaisesRegex(ValueError, "malformed"):
            publish(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_preexisting_public_destination_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("unchanged")
        with self.assertRaisesRegex(ValueError, "fresh publication root"):
            publish(self.source, self.output)
        self.assertEqual(marker.read_text(), "unchanged")

    def test_missing_native_receipt_rejected(self):
        (self.bridge / "native-alpha-pass.txt").unlink()
        with self.assertRaisesRegex(ValueError, "unexpected"):
            publish(self.source, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
