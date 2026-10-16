"""Synthetic-only tests for read-only asset inventory."""
import tempfile
import unittest
from pathlib import Path
from tools.inventory_game_files import detect_magic, inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_known_magic(self):
        self.assertEqual(detect_magic(b"\x00PSF\x01\x00\x00\x00"), "PS3_PARAM_SFO")
        self.assertEqual(detect_magic(b"SCE\x00abc"), "PS3_SELF_SPRX")
        self.assertEqual(detect_magic(b"\x7fPKGxxxx"), "PS3_PKG")
        self.assertEqual(detect_magic(b"DDS xxxx"), "DDS_TEXTURE")
        self.assertEqual(detect_magic(b"\x89PNG\r\n\x1a\nzzz"), "PNG_IMAGE")
        self.assertEqual(detect_magic(b"RIFF1234WAVE"), "WAV_AUDIO")
        self.assertEqual(detect_magic(b"PSMFdemo"), "PSMF_VIDEO")
        self.assertEqual(detect_magic(b"not-a-known-format"), "unknown")

    def test_summary_and_private_omission(self):
        (self.root / "PARAM.SFO").write_bytes(b"\x00PSF" + b"\x00" * 12)
        (self.root / "texture.dds").write_bytes(b"DDS " + b"\x01" * 12)
        (self.root / "map.bin").write_bytes(b"\x01\x02\x03")
        (self.root / "license.rap").write_bytes(b"confidential")
        report = inventory(self.root)
        self.assertEqual(report["file_count"], 3)
        self.assertEqual(report["total_bytes"], 35)
        self.assertEqual(report["signature_counts"]["PS3_PARAM_SFO"], 1)
        self.assertEqual(report["signature_counts"]["DDS_TEXTURE"], 1)
        self.assertEqual(report["signature_counts"]["unknown"], 1)
        self.assertEqual(report["skipped_sensitive"], 1)
        self.assertNotIn("sample_files", report)
        self.assertNotIn("license.rap", str(report))

    def test_optional_paths_are_relative(self):
        p = self.root / "USRDIR"
        p.mkdir()
        (p / "map.bin").write_bytes(b"abc")
        r = inventory(self.root, include_paths=True)
        self.assertEqual(r["sample_files"][0]["relative_path"], "USRDIR/map.bin")
        self.assertNotIn(str(self.root), str(r))

    def test_skips_symlinks(self):
        (self.root / "real.bin").write_bytes(b"test")
        (self.root / "link.bin").symlink_to(self.root / "real.bin")
        r = inventory(self.root)
        self.assertEqual(r["file_count"], 1)
        self.assertEqual(r["skipped_symlinks"], 1)

    def test_missing_directory_rejected(self):
        with self.assertRaisesRegex(ValueError, "existing directory"):
            inventory(self.root / "missing")


if __name__ == "__main__":
    unittest.main()
