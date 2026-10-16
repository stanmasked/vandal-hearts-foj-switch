"""Generated model/animation header fixtures, never actual game bytes."""
import struct
import unittest

from tools.inspect_bmodel_banim import (
    UnsupportedHeader, inspect_banim, inspect_bmodel, inspect_resource_header,
)


class FoJModelAnimHeaderTests(unittest.TestCase):
    def test_model_first_shape_and_candidate_count(self):
        name = b"banditShape_0"
        data = b"\x0b\x09\x00\x03\x01\x20\x00" + bytes([len(name)]) + name
        data += b"\x02\x00" + bytes(40)
        report = inspect_bmodel(data)
        self.assertEqual(report["candidate_part_count"], 3)
        self.assertEqual(report["first_shape_name"], "banditShape_0")
        self.assertEqual(report["first_shape_name_length"], len(name))
        self.assertEqual(inspect_resource_header("model.bmodel", data), report)

    def test_reject_model_truncated_or_nonprintable(self):
        name = b"unitShape_0"
        data = b"\x0b\x09\x00\x01\x01\x20\x00" + bytes([len(name)]) + name
        for payload in (data[:4], data[:12], b"\x00" + data[1:]):
            with self.assertRaises(UnsupportedHeader):
                inspect_bmodel(payload)
        bad = data[:8] + b"\x01" + data[9:]
        with self.assertRaisesRegex(UnsupportedHeader, "Non-printable"):
            inspect_bmodel(bad)

    def test_animation_candidate_duration(self):
        # 2.1 seconds is plausible for an invented animation fixture.
        data = b"\x0d" + struct.pack("<f", 2.1) + b"\x2c\x00\x00\x00\x00"
        report = inspect_banim(data)
        self.assertAlmostEqual(report["candidate_duration_seconds"], 2.1, places=4)
        self.assertEqual(report["header_variant"], 0x2c)
        self.assertEqual(inspect_resource_header("dance.banim", data), report)

    def test_invalid_animation_data(self):
        for seconds in (0, -1, 9999, float("inf"), float("nan")):
            with self.assertRaises(UnsupportedHeader):
                inspect_banim(b"\x0d" + struct.pack("<f", seconds) +
                              b"\x1c\x00\x00\x00\x00")
        with self.assertRaises(UnsupportedHeader):
            inspect_banim(b"\x0d\x00")

    def test_unknown_extension(self):
        with self.assertRaises(UnsupportedHeader):
            inspect_resource_header("invalid.bin", b"\x0d" + b"\x00" * 30)


if __name__ == "__main__":
    unittest.main()
