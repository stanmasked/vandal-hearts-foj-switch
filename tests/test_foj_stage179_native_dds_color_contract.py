"""Native C atlas decode vs independently generated Python pixels.

Generated-only images. This checks CPU channel order and exact bytes,
not a Nintendo Switch GPU draw, shader execution, or game asset.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from tools.foj_stage162_synthetic_dds import generated_dds

ROOT = Path(__file__).resolve().parents[1]
HEADER = 128
PIXELS = 8 * 8 * 4
EXPECTED_FIRST = ((255, 215, 70, 255), (70, 235, 220, 255))
EXPECTED_CHECKED = ((240, 45, 30, 255), (35, 95, 235, 255))


class Stage179NativeDdsColorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.probe = str(Path(cls.tmp.name) / "foj-native-synthetic-pixels")
        cc = shutil.which("cc")
        if not cc:
            cls.tmp.cleanup()
            raise unittest.SkipTest("Host C compiler unavailable")
        built = subprocess.run(
            [
                cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                "-Igpu", "tests/foj_stage179_native_dds_pixels.c",
                "gpu/atlas_dds.c", "-o", cls.probe,
            ],
            cwd=ROOT, text=True, capture_output=True,
        )
        if built.returncode:
            cls.tmp.cleanup()
        assert built.returncode == 0, built.stderr

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "tmp", None):
            cls.tmp.cleanup()

    @classmethod
    def decode(cls, blob: bytes):
        return subprocess.run(
            [cls.probe], input=blob, cwd=ROOT, capture_output=True,
        )

    def test_both_python_checkerboards_match_native_rgba_pixels_exactly(self):
        results = []
        for slot in (0, 1):
            with self.subTest(slot=slot):
                generated = generated_dds(slot)
                self.assertEqual(len(generated), HEADER + PIXELS)
                native = self.decode(generated)
                self.assertEqual(native.returncode, 0, native.stderr)
                self.assertEqual(native.stderr, b"")
                self.assertEqual(native.stdout, generated[HEADER:])
                self.assertEqual(len(native.stdout), PIXELS)
                self.assertEqual(tuple(native.stdout[:4]), EXPECTED_FIRST[slot])
                # 2x2-block checkerboard flips at x=2.
                self.assertEqual(tuple(native.stdout[2*4:3*4]),
                                 EXPECTED_CHECKED[slot])
                results.append(hashlib.sha256(native.stdout).hexdigest())
        self.assertNotEqual(results[0], results[1])

    def test_native_bgra_conversion_matches_unmodified_rgba_reference(self):
        for slot in (0, 1):
            with self.subTest(slot=slot):
                canonical = generated_dds(slot)
                bgra = bytearray(canonical)
                struct.pack_into("<I", bgra, 92, 0x00ff0000)
                struct.pack_into("<I", bgra, 100, 0x000000ff)
                for offset in range(HEADER, len(bgra), 4):
                    bgra[offset], bgra[offset+2] = bgra[offset+2], bgra[offset]
                result = self.decode(bytes(bgra))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, canonical[HEADER:])

    def test_short_extra_and_invalid_magic_emit_no_pixels(self):
        valid = generated_dds(0)
        cases = (valid[:-1], valid+b"\x00", b"\x00"+valid[1:], b"", b"DDS ")
        for blob in cases:
            with self.subTest(size=len(blob)):
                result = self.decode(blob)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")

    def test_noncanonical_channel_masks_and_dx10_tag_rejected(self):
        valid = generated_dds(1)
        for offset, value in ((92, 0x0000ffff), (100, 0x000000ff),
                              (84, 0x30315844), (16, 12)):
            with self.subTest(offset=offset):
                bad = bytearray(valid)
                struct.pack_into("<I", bad, offset, value)
                result = self.decode(bytes(bad))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")

    def test_pixel_data_change_is_visible_not_silently_normalized(self):
        valid = generated_dds(1)
        changed = bytearray(valid)
        changed[HEADER+1] ^= 0x3f
        original = self.decode(valid)
        altered = self.decode(bytes(changed))
        self.assertEqual(original.returncode, 0)
        self.assertEqual(altered.returncode, 0)
        self.assertNotEqual(altered.stdout, original.stdout)
        self.assertEqual(altered.stdout, bytes(changed)[HEADER:])


if __name__ == "__main__":
    unittest.main()
