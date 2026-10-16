"""Generated UAM-like DKSH fixtures only, no commercial game data."""
from pathlib import Path
import tempfile
import unittest

from tests.test_validate_dksh import fixture
from tools.prepare_gpu_triangle_sd import (
    RELATIVE_FOLDER, prepare_triangle_shaders,
)
from tools.validate_dksh import DkshError


class GpuTriangleSdBundleTests(unittest.TestCase):
    def test_generated_shader_pair_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vert, frag = root / "vs.dksh", root / "fs.dksh"
            vert.write_bytes(fixture(stage=0))
            frag.write_bytes(fixture(stage=1))
            result = prepare_triangle_shaders(vert, frag, root)
            target = root / RELATIVE_FOLDER
            self.assertEqual(
                (target / "foj_actor.vert.dksh").read_bytes(),
                vert.read_bytes()
            )
            self.assertEqual(
                (target / "foj_triangle.frag.dksh").read_bytes(),
                frag.read_bytes()
            )
            self.assertEqual([s["stage"] for s in result["shaders"]],
                             ["vertex", "fragment"])
            with self.assertRaises(FileExistsError):
                prepare_triangle_shaders(vert, frag, root)

    def test_rejects_wrong_stage_without_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vert, frag = root / "vs.dksh", root / "fs.dksh"
            vert.write_bytes(fixture(stage=1))
            frag.write_bytes(fixture(stage=1))
            with self.assertRaisesRegex(DkshError, "Expected"):
                prepare_triangle_shaders(vert, frag, root)
            self.assertFalse((root / RELATIVE_FOLDER).exists())

    def test_rejects_large_module_before_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vert, frag = root / "vs.dksh", root / "fs.dksh"
            vert.write_bytes(fixture(stage=0))
            frag.write_bytes(b"X" * (126976 + 1))
            with self.assertRaisesRegex(DkshError, "slot"):
                prepare_triangle_shaders(vert, frag, root)
            self.assertFalse((root / RELATIVE_FOLDER).exists())

    def test_rejects_nonexistent_output_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            vert, frag = root / "vs.dksh", root / "fs.dksh"
            vert.write_bytes(fixture(stage=0))
            frag.write_bytes(fixture(stage=1))
            with self.assertRaisesRegex(ValueError, "Output directory"):
                prepare_triangle_shaders(vert, frag, root / "nonexistent")


if __name__ == "__main__":
    unittest.main()
