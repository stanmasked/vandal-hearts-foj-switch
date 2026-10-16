"""Nested synthetic PS3 archive contains only generated BANIM key data."""
import tempfile
import unittest
from pathlib import Path

from tests.test_decode_rig_banim import synthetic_banim
from tests.test_inspect_debug_pkg_assets import make_parts, synthetic_pkg
from tools.export_local_banim import export_local_banim


class LocalAnimationExportTests(unittest.TestCase):
    def test_export_single_valid_animation_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            parts = make_parts(directory, synthetic_pkg(with_animation=True))
            output = Path(directory) / "preview.banim"
            result = export_local_banim(
                parts, "data/actors/anims/synthetic_test.banim", output
            )
            self.assertEqual(result["tracks"], 2)
            self.assertEqual(result["keys"], 3)
            self.assertEqual(output.read_bytes(), synthetic_banim())
            with self.assertRaises(FileExistsError):
                export_local_banim(
                    parts, "data/actors/anims/synthetic_test.banim", output
                )
            with self.assertRaises(ValueError):
                export_local_banim(
                    parts, "../secrets.banim", Path(directory) / "bad.banim"
                )
            self.assertEqual(len(list(Path(directory).glob("*.banim"))), 1)


if __name__ == "__main__":
    unittest.main()
