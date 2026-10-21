"""Stage292 synthetic fixture parity against the real native C DDS loader."""
from __future__ import annotations

import ctypes
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
import struct
import unittest

from tools.foj_gpu_local_dds_preflight import classify_classic_dds
from tools.foj_stage292_synthetic_gtf_dds_roundtrip import (
    TAG, canonical_rgba, convert_fixture, generate_fixture, main,
)


class Stage292SyntheticConversionTests(unittest.TestCase):
    def case(self, width=64, height=64, mips=1, opaque=False):
        dds, proof = convert_fixture(generate_fixture(width, height, mips, opaque))
        self.assertEqual(dds[128:128 + width * height * 4],
                         canonical_rgba(width, height, mips, opaque)[:width * height * 4])
        self.assertEqual(proof["output_format"], "native-loader-compatible-RGBA8-DDS")
        self.assertFalse(proof["original_ps3_resources_processed"])
        self.assertFalse(proof["production_game_conversion_permitted"])
        self.assertEqual(classify_classic_dds(dds)["declared_mip_levels"], mips)
        return dds

    def mutated(self, offset, byte, source=None):
        buffer = bytearray(generate_fixture() if source is None else source)
        buffer[offset] = byte
        return bytes(buffer)

    def test_64_square_single_level_mixed_alpha(self):
        self.case()
    def test_64_square_opaque(self):
        self.case(opaque=True)
    def test_small_8x1_single_level(self):
        self.case(8, 1)
    def test_24x13_three_mips(self):
        self.case(24, 13, 3)
    def test_64_square_full_seven_level_chain(self):
        self.case(64, 64, 7)
    def test_256_square_nine_levels_maximum(self):
        self.case(256, 256, 9)

    def test_distinct_rgb_channels_survive_mapping(self):
        dds = self.case(8, 8)
        rgba = canonical_rgba(8, 8, 1, False)
        self.assertNotEqual(rgba[0], rgba[2])
        self.assertEqual(dds[128:132], rgba[:4])
        self.assertEqual(generate_fixture(8, 8)[128:132],
                         bytes((rgba[2], rgba[1], rgba[0], rgba[3])))

    def test_full_alpha_profile_is_preserved(self):
        mixed = self.case(16, 8, opaque=False)
        rear = self.case(16, 8, opaque=True)
        self.assertIn(128, mixed[131::4])
        self.assertTrue(all(a == 255 for a in rear[131::4]))

    def test_mips_have_distinct_correct_bytes(self):
        dds = self.case(16, 8, 3)
        expected = canonical_rgba(16, 8, 3, False)
        self.assertEqual(dds[128:], expected)
        self.assertEqual(struct.unpack_from("<I", dds, 108)[0], 0x401008)
        self.assertEqual(struct.unpack_from("<I", dds, 8)[0], 0x2100f)

    def test_actual_ps3_without_marker_is_rejected(self):
        data = bytearray(generate_fixture())
        data[64:64 + len(TAG)] = bytes(len(TAG))
        with self.assertRaisesRegex(ValueError, "non-synthetic"):
            convert_fixture(bytes(data))

    def test_nonbytes_input_rejected(self):
        with self.assertRaises(ValueError):
            convert_fixture(bytearray(generate_fixture()))

    def test_other_version_rejected(self):
        with self.assertRaises(ValueError):
            convert_fixture(self.mutated(0, 0))

    def test_other_format_rejected(self):
        with self.assertRaisesRegex(ValueError, "header"):
            convert_fixture(self.mutated(36, 0x85))

    def test_unsupported_linear_bc1_rejected(self):
        with self.assertRaises(ValueError):
            convert_fixture(self.mutated(36, 0xA6))

    def test_bad_channel_profile_rejected(self):
        with self.assertRaises(ValueError):
            convert_fixture(self.mutated(56, 9))

    def test_invented_header_unknown_byte_rejected(self):
        with self.assertRaises(ValueError):
            convert_fixture(self.mutated(57, 1))

    def test_bad_pitch_rejected(self):
        with self.assertRaises(ValueError):
            convert_fixture(self.mutated(50, 0))

    def test_claimed_payload_overflow_rejected(self):
        with self.assertRaises(ValueError):
            convert_fixture(self.mutated(23, 1))

    def test_changed_pixel_bytes_rejected(self):
        src = generate_fixture()
        with self.assertRaisesRegex(ValueError, "invented pixel"):
            convert_fixture(self.mutated(128, src[128] ^ 1, src))

    def test_truncation_and_extension_rejected(self):
        src = generate_fixture()
        with self.assertRaises(ValueError):
            convert_fixture(src[:-1])
        with self.assertRaises(ValueError):
            convert_fixture(src + b"X")

    def test_mips_beyond_possible_rejected(self):
        with self.assertRaises(ValueError):
            generate_fixture(8, 1, 9)

    def test_input_dimensions_outside_native_limits_rejected(self):
        with self.assertRaises(ValueError):
            generate_fixture(7, 64)
        with self.assertRaises(ValueError):
            generate_fixture(264, 64)
        with self.assertRaises(ValueError):
            generate_fixture(64, 257)

    def test_cli_never_writes_or_prints_pixels(self):
        output, err = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(err):
            status = main(["--width", "24", "--height", "13", "--mips", "3"])
        self.assertEqual(status, 0)
        self.assertEqual(err.getvalue(), "")
        data = json.loads(output.getvalue())
        self.assertEqual(data["mip_levels"], 3)
        self.assertFalse(data["production_game_conversion_permitted"])
        self.assertNotIn("sha256", output.getvalue())

    def test_cli_invalid_is_fail_closed(self):
        output, err = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(err):
            status = main(["--width", "7"])
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("refused", err.getvalue())

    def test_deterministic_reproducibility(self):
        for width, height, mips in ((8, 1, 1), (24, 13, 3), (64, 64, 7)):
            self.assertEqual(generate_fixture(width, height, mips),
                             generate_fixture(width, height, mips))
            self.assertEqual(convert_fixture(generate_fixture(width, height, mips))[0],
                             convert_fixture(generate_fixture(width, height, mips))[0])


class NativeDDSSmokeTests(unittest.TestCase):
    class Info(ctypes.Structure):
        _fields_ = [("width", ctypes.c_uint), ("height", ctypes.c_uint),
                    ("pixel_bytes", ctypes.c_size_t)]

    @classmethod
    def setUpClass(cls):
        path = os.environ.get("FOJ_STAGE292_ATLAS_SO")
        if not path:
            raise RuntimeError("Stage292 must exercise the real compiled native C loader")
        cls.dll = ctypes.CDLL(path)
        cls.fn = cls.dll.foj_atlas_dds_decode
        byteptr = ctypes.POINTER(ctypes.c_uint8)
        cls.fn.argtypes = [byteptr, ctypes.c_size_t, byteptr,
                           ctypes.c_size_t, ctypes.POINTER(cls.Info)]
        cls.fn.restype = ctypes.c_int

    def decode(self, dds, width, height):
        src = (ctypes.c_uint8 * len(dds)).from_buffer_copy(dds)
        cap = width * height * 4
        dst = (ctypes.c_uint8 * cap)()
        info = self.Info()
        value = self.fn(src, len(dds), dst, cap, ctypes.byref(info))
        self.assertEqual(value, 1)
        self.assertEqual((info.width, info.height, info.pixel_bytes),
                         (width, height, cap))
        return bytes(dst)

    def test_real_native_c_base_pixels_and_alpha(self):
        for width, height, mips, opaque in (
            (8, 1, 1, False), (24, 13, 3, False),
            (64, 64, 7, True), (256, 256, 9, False),
        ):
            with self.subTest(dimensions=(width, height), mips=mips):
                dds, _ = convert_fixture(generate_fixture(width, height, mips, opaque))
                actual = self.decode(dds, width, height)
                expected = canonical_rgba(width, height, mips, opaque)
                self.assertEqual(actual, expected[:width * height * 4])

    def test_native_c_rejects_corrupt_dds_without_modifying_output(self):
        dds, _ = convert_fixture(generate_fixture(16, 8, 3))
        corrupt = bytearray(dds)
        corrupt[108] = 0
        src = (ctypes.c_uint8 * len(corrupt)).from_buffer_copy(corrupt)
        cap = 16 * 8 * 4
        dst = (ctypes.c_uint8 * cap)(*([0xA5] * cap))
        info = self.Info(1234, 5678, 999)
        result = self.fn(src, len(corrupt), dst, cap, ctypes.byref(info))
        self.assertEqual(result, 0)
        self.assertEqual(bytes(dst), b"\xA5" * cap)
        self.assertEqual((info.width, info.height, info.pixel_bytes),
                         (1234, 5678, 999))


if __name__ == "__main__":
    unittest.main()
