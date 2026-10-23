#!/usr/bin/env python3
"""Generated-only PSARC short-tail tests. Never reads original game files."""
import unittest
import zlib
from tools.inspect_debug_pkg_assets import PSARC, FormatError


class FakePackage:
    def __init__(self, data):
        self.data = data

    def read(self, pos, count):
        if pos < 0 or count < 0 or pos + count > len(self.data):
            raise ValueError("test file bounds")
        return self.data[pos:pos + count]


def synthetic_archive(data, block_lengths, expected_length):
    archive = PSARC.__new__(PSARC)
    archive.pkg = FakePackage(data)
    archive.start = 0
    archive.size = len(data)
    archive.block_size = 1024
    archive.blocks = block_lengths
    archive.entries = [{"offset": 0, "zindex": 0, "length": expected_length}]
    return archive


class PSARCTailTests(unittest.TestCase):
    def test_raw_final_partial_block_with_explicit_byte_count(self):
        prefix = bytes((i * 73 + 17) % 256 for i in range(1024))
        tail = bytes((i * 19 + 35) % 256 for i in range(160))
        reader = synthetic_archive(prefix + tail, [0, 160], 1184)
        self.assertEqual(reader.entry_data(0), prefix + tail)

    def test_compressed_tail_still_decodes(self):
        payload = (b"safe-synthetic-sequence" * 7)[:160]
        packed = zlib.compress(payload)
        reader = synthetic_archive(packed, [len(packed)], len(payload))
        self.assertEqual(reader.entry_data(0), payload)

    def test_uncompressed_full_block_zero_marker(self):
        payload = bytes((i * 11 + 5) % 256 for i in range(1024))
        reader = synthetic_archive(payload, [0], 1024)
        self.assertEqual(reader.entry_data(0), payload)

    def test_partial_block_length_too_short_rejected(self):
        data = bytes((i * 13 + 1) % 256 for i in range(159))
        reader = synthetic_archive(data, [159], 160)
        with self.assertRaises(FormatError):
            reader.entry_data(0)

    def test_corrupted_zlib_header_must_not_fall_back(self):
        data = b"\x78\x9c" + b"X" * 158
        reader = synthetic_archive(data, [160], 160)
        with self.assertRaises(FormatError):
            reader.entry_data(0)

    def test_corrupt_overexpanding_zlib_tail_refused(self):
        data = zlib.compress(b"X" * 161)
        reader = synthetic_archive(data, [len(data)], 160)
        with self.assertRaises(FormatError):
            reader.entry_data(0)

    def test_refuse_trailing_short_raw_as_full_compressed_block(self):
        data = bytes((i * 13 + 1) % 256 for i in range(160))
        reader = synthetic_archive(data, [160], 1024)
        with self.assertRaises(FormatError):
            reader.entry_data(0)


if __name__ == "__main__":
    unittest.main()
