"""Read-only validation and local-only export tested with entirely synthetic data."""
from pathlib import Path
import struct
import tempfile
import unittest

from tests.test_inspect_debug_pkg_assets import make_parts, synthetic_pkg
from tools.export_local_texture import (
    export_local_texture,
    validate_legacy_dds,
)
from tools.inspect_debug_pkg_assets import FormatError


class LocalDDSTextureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def test_full_local_export_and_no_overwrite(self):
        parts = make_parts(self.tmp.name, synthetic_pkg())
        path = self.directory / "preview.tga"
        result = export_local_texture(parts, "data/example.tga", path)
        self.assertEqual(result["format"], "BGRA8")
        self.assertEqual((result["width"], result["height"]), (4, 4))
        self.assertTrue(path.exists())
        self.assertEqual(result["bytes_written"], len(path.read_bytes()))
        self.assertTrue(path.read_bytes().startswith(b"DDS "))
        with self.assertRaises(FileExistsError):
            export_local_texture(parts, "data/example.tga", path)
        with self.assertRaises(ValueError):
            export_local_texture(parts, "../wrong.tga",
                                 self.directory / "wrong.tga")
        self.assertEqual(len(list(self.directory.glob("*.tga"))), 1)

    def test_dxt1_validation(self):
        blob = bytearray(136)
        blob[:4] = b"DDS "
        struct.pack_into("<I", blob, 4, 124)
        struct.pack_into("<II", blob, 12, 4, 4)
        struct.pack_into("<I", blob, 76, 32)
        struct.pack_into("<II", blob, 80, 4, 0x31545844)
        result = validate_legacy_dds(bytes(blob))
        self.assertEqual(result["format"], "DXT1")
        with self.assertRaisesRegex(FormatError, "Truncated"):
            validate_legacy_dds(bytes(blob[:-1]))

    def test_unknown_bgra_mask_fails(self):
        blob = bytearray(128 + 64)
        blob[:4] = b"DDS "
        struct.pack_into("<I", blob, 4, 124)
        struct.pack_into("<II", blob, 12, 4, 4)
        struct.pack_into("<I", blob, 76, 32)
        struct.pack_into("<II", blob, 80, 0x41, 0)
        struct.pack_into("<I", blob, 88, 32)
        with self.assertRaisesRegex(FormatError, "Only BGRA8"):
            validate_legacy_dds(bytes(blob))


if __name__ == "__main__":
    unittest.main()
