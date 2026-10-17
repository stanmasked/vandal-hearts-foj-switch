"""Fixtures contain only invented bytes. No user-owned PS3 content."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.foj_texture_probe import (
    CHUNK_SIZE, HEADER_SIZE, inventory, iter_candidate_headers,
    parse_dds_candidate,
)


def put32(buffer, offset, value):
    struct.pack_into("<I", buffer, offset, value)


def dds_header(*, width=8, height=8, fourcc=b"DXT1", mip_count=1):
    data = bytearray(HEADER_SIZE)
    data[:4] = b"DDS "
    put32(data, 4, 124)
    put32(data, 8, 0x81007)
    put32(data, 12, height)
    put32(data, 16, width)
    put32(data, 20, ((width + 3) // 4) * ((height + 3) // 4) * 8)
    put32(data, 28, mip_count)
    put32(data, 76, 32)
    put32(data, 80, 4)
    data[84:88] = fourcc
    put32(data, 108, 0x1000)
    return bytes(data)


class TextureProbeTests(unittest.TestCase):
    def test_start_of_file_and_metadata(self):
        h = dds_header()
        candidate = parse_dds_candidate(h, offset=0, file_bytes=128 + 32)
        self.assertEqual(candidate["format_candidate"], "BC1/DXT1")
        self.assertEqual(candidate["expected_payload_bytes"], 32)
        self.assertEqual(candidate["payload_check"], "ends-at-file-boundary")
        self.assertEqual(candidate["location"], "file-start")
        self.assertEqual(candidate["declared_mip_levels"], 1)

    def test_embedded_and_extended_payload(self):
        h = dds_header(fourcc=b"DXT5")
        c = parse_dds_candidate(h, offset=17, file_bytes=17 + 128 + 64 + 5)
        self.assertEqual(c["format_candidate"], "BC3/DXT5")
        self.assertEqual(c["payload_check"], "additional-bytes-after-declared-mips")
        self.assertEqual(c["location"], "embedded")
        truncated = parse_dds_candidate(h, offset=17, file_bytes=17 + 128 + 7)
        self.assertEqual(truncated["payload_check"], "truncated")

    def test_invalid_and_unknown_are_not_misreported_as_supported(self):
        h = bytearray(dds_header())
        put32(h, 4, 100)
        self.assertIsNone(parse_dds_candidate(h, offset=0, file_bytes=500))
        h = bytearray(dds_header(fourcc=b"ZZZZ"))
        result = parse_dds_candidate(h, offset=0, file_bytes=500)
        self.assertEqual(result["format_candidate"], "FourCC/5a5a5a5a")
        self.assertIsNone(result["expected_payload_bytes"])

    def test_bgra_header_and_mip_sizes(self):
        h = bytearray(dds_header())
        put32(h, 80, 0x41)
        h[84:88] = b"\0\0\0\0"
        put32(h, 88, 32)
        for position, mask in zip((92, 96, 100, 104),
                                   (0xff0000, 0xff00, 0xff, 0xff000000)):
            put32(h, position, mask)
        put32(h, 28, 4)
        result = parse_dds_candidate(bytes(h), offset=0,
                                     file_bytes=128 + 256 + 64 + 16 + 4)
        self.assertEqual(result["format_candidate"], "BGRA8")
        self.assertEqual(result["expected_payload_bytes"], 340)
        self.assertEqual(result["payload_check"], "ends-at-file-boundary")

    def test_stream_boundary_overlap_and_deterministic_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # DDS magic begins three bytes before a 1-MiB chunk boundary.
            prefix = b"X" * (CHUNK_SIZE - 3)
            (root / "z_embedded.bin").write_bytes(prefix + dds_header() + b"\0" * 32)
            (root / "a_start.dds").write_bytes(dds_header() + b"\0" * 32)
            (root / "b_noise.bin").write_bytes(b"some DDS garbage")
            candidates = list(iter_candidate_headers(root / "z_embedded.bin"))
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0][0], CHUNK_SIZE - 3)
            info = inventory(root)
            self.assertEqual(info["files_scanned"], 3)
            self.assertEqual(len(info["candidates"]), 2)
            self.assertEqual([c["relative_path"] for c in info["candidates"]],
                             ["a_start.dds", "z_embedded.bin"])
            self.assertEqual(info["candidates"][1]["offset"], CHUNK_SIZE - 3)
            self.assertEqual(info["candidates"][1]["payload_check"],
                             "ends-at-file-boundary")
            self.assertEqual(info, inventory(root))

    def test_limits_and_read_only_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a_large.bin").write_bytes(b"X" * 1024)
            (root / "b.dds").write_bytes(dds_header() + b"\0" * 32)
            report = inventory(root, max_file_bytes=500, max_files=1)
            self.assertEqual(report["skipped_large"], 1)
            self.assertEqual(report["files_scanned"], 1)
            self.assertEqual(len(report["candidates"]), 1)
            self.assertFalse(report["scan_truncated_at_file_limit"])

    def test_cli_report_has_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = dds_header() + b"PRIVATE-ASSET-DATA" + b"\0" * 14
            (root / "private.dds").write_bytes(data)
            report_file = root.parent / (root.name + "_metadata.json")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "tools.foj_texture_probe", str(root),
                     "--output", str(report_file)],
                    check=True, capture_output=True, text=True)
                self.assertIn("found 1 possible DDS headers", result.stdout)
                text = report_file.read_text(encoding="utf-8")
                manifest = json.loads(text)
                self.assertEqual(len(manifest["candidates"]), 1)
                self.assertNotIn("PRIVATE-ASSET-DATA", text)
                self.assertNotIn(str(root), text)
            finally:
                report_file.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
