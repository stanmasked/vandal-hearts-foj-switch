"""Stage-162 generated checkerboards and privacy-safe SD staging checks."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stage162_synthetic_dds import generated_dds, publish_generated_pair
from tools.foj_gpu_local_dds_preflight import (
    classify_classic_dds, examine_local_slots,
)


class Stage162GeneratedSmokeDdsTests(unittest.TestCase):
    def test_two_distinct_synthetic_patterns_are_classic_rgba8(self):
        left = generated_dds(0)
        right = generated_dds(1)
        self.assertEqual(len(left), 384)
        self.assertEqual(len(right), 384)
        self.assertNotEqual(left, right)
        self.assertEqual(left[:128], right[:128])
        self.assertNotEqual(left[128:], right[128:])
        for blob in (left, right):
            result = classify_classic_dds(blob)
            self.assertEqual(result["width"], 8)
            self.assertEqual(result["height"], 8)
            self.assertEqual(result["format"], "RGBA8")
            self.assertEqual(result["dds_file_bytes"], 384)
            self.assertEqual(result["declared_mip_levels"], 1)

    def test_checkerboard_has_two_distinct_colors_per_slot(self):
        for slot in (0, 1):
            pixels = generated_dds(slot)[128:]
            values = {pixels[i:i + 4] for i in range(0, len(pixels), 4)}
            self.assertEqual(len(values), 2)
            self.assertTrue(all(pixel[-1] == 255 for pixel in values))

    def test_reject_unknown_slot_and_wrong_types(self):
        for slot in (-1, 2, True, None, "0"):
            with self.subTest(slot=slot), self.assertRaises(ValueError):
                generated_dds(slot)

    def test_publish_pair_and_preflight_together(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "fresh-generated-dds"
            report = publish_generated_pair(folder)
            self.assertEqual(len(report["slots"]), 2)
            self.assertEqual([p["status"] for p in report["slots"]],
                             ["classic-dds-compatible"] * 2)
            for i in (0, 1):
                self.assertEqual((folder / f"material{i}.dds").read_bytes(),
                                 generated_dds(i))
            self.assertEqual(examine_local_slots(folder), report)

    def test_never_overwrite_existing_directory_or_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "existing"
            folder.mkdir()
            original = folder / "material0.dds"
            original.write_bytes(b"PRIVATE-CONTENT-DO-NOT-OVERWRITE")
            with self.assertRaisesRegex(ValueError, "must be new"):
                publish_generated_pair(folder)
            self.assertEqual(original.read_bytes(),
                             b"PRIVATE-CONTENT-DO-NOT-OVERWRITE")

    def test_cli_is_idempotently_rejected_on_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "generated"
            command = [
                sys.executable, "-m", "tools.foj_stage162_synthetic_dds",
                str(folder),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("generated-only", first.stdout)
            before = [(folder / f"material{i}.dds").read_bytes()
                      for i in (0, 1)]
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            after = [(folder / f"material{i}.dds").read_bytes()
                     for i in (0, 1)]
            self.assertEqual(before, after)
            self.assertNotIn(str(folder), repeated.stderr)

    def test_cli_preflight_accepts_generated_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "generated"
            publish_generated_pair(folder)
            check = subprocess.run([
                sys.executable, "-m", "tools.foj_gpu_local_dds_preflight",
                str(folder),
            ], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("classic-dds-compatible", check.stdout)
            self.assertNotIn(str(folder), check.stdout)


if __name__ == "__main__":
    unittest.main()
