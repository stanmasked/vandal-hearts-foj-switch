"""Synthetic NRO header tests; no commercial binary samples."""
import struct
import unittest

from tools.validate_nro import validate_nro


def fake_nro():
    data = bytearray(0x200)
    data[0x10:0x14] = b"NRO0"
    struct.pack_into("<I", data, 0x18, 0x200)
    for offset, seg in ((0x20, (0x80, 0x30)), (0x28, (0xB0, 0x30)), (0x30, (0xE0, 0x20))):
        struct.pack_into("<II", data, offset, *seg)
    return data


class NROTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_nro(fake_nro())["declared_size"], 0x200)

    def test_bad_magic(self):
        data = fake_nro()
        data[0x10] = 0
        with self.assertRaisesRegex(ValueError, "magic"):
            validate_nro(data)

    def test_truncated(self):
        with self.assertRaisesRegex(ValueError, "Truncated"):
            validate_nro(b"NRO0")

    def test_bad_segment(self):
        data = fake_nro()
        struct.pack_into("<II", data, 0x28, 0x1F0, 0x30)
        with self.assertRaisesRegex(ValueError, "rodata"):
            validate_nro(data)

    def test_bad_declared_size(self):
        data = fake_nro()
        struct.pack_into("<I", data, 0x18, 0x210)
        with self.assertRaisesRegex(ValueError, "declared size"):
            validate_nro(data)


if __name__ == "__main__":
    unittest.main()
