import struct
import unittest
import zlib

from tools.ppm_to_png import PNG_MAGIC, ppm_to_png


class PreviewPNGTests(unittest.TestCase):
    def test_known_two_pixel_image(self):
        ppm = b"P6\n2 1\n255\n" + bytes([255, 0, 0, 0, 255, 0])
        png = ppm_to_png(ppm)
        self.assertTrue(png.startswith(PNG_MAGIC))
        ihdr_length = struct.unpack(">I", png[8:12])[0]
        self.assertEqual(ihdr_length, 13)
        self.assertEqual(png[12:16], b"IHDR")
        self.assertEqual(struct.unpack(">2I", png[16:24]), (2, 1))
        self.assertEqual(png[24:26], bytes([8, 6]))
        index = png.index(b"IDAT")
        length = struct.unpack(">I", png[index - 4:index])[0]
        payload = png[index + 4:index + 4 + length]
        self.assertEqual(
            zlib.decompress(payload),
            b"\x00\xff\x00\x00\xff\x00\xff\x00\xff",
        )

    def test_reject_bad_format(self):
        with self.assertRaises(ValueError):
            ppm_to_png(b"P3\n2 1\n255\n123456")

    def test_reject_mismatched_size(self):
        with self.assertRaisesRegex(ValueError, "pixel bytes"):
            ppm_to_png(b"P6\n2 1\n255\n" + b"\x00" * 3)

    def test_reject_excessive_dimensions(self):
        with self.assertRaises(ValueError):
            ppm_to_png(b"P6\n99999 1\n255\n")


if __name__ == "__main__":
    unittest.main()
