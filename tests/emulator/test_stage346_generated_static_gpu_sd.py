"""Stage346 generated-only static mesh fixture tests."""
from pathlib import Path
import struct
import tempfile
import unittest

from tools.foj_stage346_generated_static_gpu_sd import (
    generated_geometry, generated_materials, generated_dds, COLORS, install_generated
)


class StaticBundleTests(unittest.TestCase):
    def test_unskinned_two_section_fojrm_and_material_mapping(self):
        mesh = generated_geometry()
        table = generated_materials()
        self.assertEqual(len(mesh), 28 + 2*8 + 6*76)
        self.assertEqual(mesh[:8], b"FOJRM001")
        self.assertEqual(struct.unpack_from("<IIIII", mesh, 8), (1, 0, 6, 2, 0))
        self.assertEqual(struct.unpack_from("<IIII", mesh, 28), (0, 3, 3, 3))
        self.assertEqual(table, b"FOJMAT01" + struct.pack("<IIII", 2, 2, 0, 1))
        for i in range(6):
            off = 44 + 76*i
            xyz = struct.unpack_from("<fff", mesh, off)
            self.assertTrue(all(-1 <= v <= 1 for v in xyz))
            self.assertEqual(struct.unpack_from("<I", mesh, off+32)[0], 0)
            for j in range(5):
                self.assertEqual(struct.unpack_from("<If", mesh, off+36+j*8), (0, 0.0))

    def test_dds_fixture_dimensions_and_payload(self):
        for color in COLORS:
            blob = generated_dds(color)
            self.assertEqual(len(blob), 128 + 64*64*4)
            self.assertEqual(blob[:4], b"DDS ")
            self.assertEqual(struct.unpack_from("<II", blob, 12), (64, 64))
            self.assertEqual(blob[128:132], bytes(color))
            self.assertEqual(blob[-4:], bytes(color))

    def test_existing_sd_root_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "private-root"
            root.mkdir()
            sentinel = root / "sentinel"
            sentinel.write_text("private")
            with self.assertRaises(ValueError):
                install_generated(root, Path(tmp) / "missing-shaders")
            self.assertEqual(sentinel.read_text(), "private")


if __name__ == "__main__":
    unittest.main()
