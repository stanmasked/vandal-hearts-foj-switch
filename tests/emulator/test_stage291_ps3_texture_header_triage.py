"""Synthetic-only Stage291 source header triage and fail-closed privacy tests."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage291_ps3_texture_header_triage import (
    CATEGORIES, PREFIX_BYTES, analyze, classify_prefix, main,
)

def fixture_v1(*, fmt=0xA5, mips=1, width=64, height=64, count=1,
               texture_offset=128, texture_bytes=64, dimension=2):
    data = bytearray(max(texture_offset + texture_bytes, PREFIX_BYTES))
    data[:4] = bytes.fromhex("02000101")
    for off, value in ((8, count), (16, texture_offset),
                       (20, texture_bytes)):
        struct.pack_into(">I", data, off, value)
    data[36] = fmt
    data[37] = mips
    data[38] = dimension
    data[39] = 0
    struct.pack_into(">HH", data, 44, width, height)
    return bytes(data)


def fixture_alt(*, count=1, descriptor_offset=128):
    data = bytearray(192)
    data[:4] = bytes.fromhex("020200ff")
    struct.pack_into(">II", data, 8, count, 0)
    struct.pack_into(">I", data, 16, descriptor_offset)
    return bytes(data)


class Stage291SyntheticHeaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "local"
        self.root.mkdir()

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_empty_is_complete_without_conversion(self):
        result = analyze(self.root)
        self.assertEqual(result["files_scanned"], 0)
        self.assertTrue(result["scan_complete_within_file_limit"])
        self.assertFalse(result["conversion_permitted"])
        self.assertFalse(result["original_ps3_texture_format_verified"])

    def test_v1_linear_rgba_version_is_only_candidate(self):
        self.put("x/a.bin", fixture_v1(fmt=0xA5))
        result = analyze(self.root)
        self.assertEqual(result["category_counts"]["gtf_v1_linear_rgba_hint"], 1)
        self.assertEqual(result["possible_gtf_container_headers"], 1)
        self.assertFalse(result["conversion_permitted"])

    def test_v1_tiled_rgba_is_blocked(self):
        self.put("t.bin", fixture_v1(fmt=0x85))
        result = analyze(self.root)
        self.assertEqual(result["category_counts"]["gtf_v1_tiled_rgba_hint"], 1)

    def test_v1_linear_bc1_bc2_bc3_are_all_only_hints(self):
        for value in (0xA6, 0xA7, 0xA8):
            self.put(f"synthetic{value}.bin", fixture_v1(fmt=value))
        seen = analyze(self.root)["category_counts"]
        self.assertEqual(seen["gtf_v1_linear_bc1_hint"], 1)
        self.assertEqual(seen["gtf_v1_linear_bc2_hint"], 1)
        self.assertEqual(seen["gtf_v1_linear_bc3_hint"], 1)

    def test_unrecognized_gpu_format_never_promoted_to_dds(self):
        self.put("unclassified.bin", fixture_v1(fmt=0x91))
        result = analyze(self.root)
        self.assertEqual(result["category_counts"]["gtf_v1_unclassified_gpu_format_hint"], 1)
        self.assertFalse(result["conversion_permitted"])

    def test_alternate_version_remains_header_hint_without_v1_decode(self):
        self.put("alt.bin", fixture_alt())
        result = analyze(self.root)
        self.assertEqual(result["category_counts"]["gtf_alt_version_header_hint"], 1)

    def test_bad_alternate_header_not_counted_as_texture(self):
        self.put("bad-alt.bin", fixture_alt(descriptor_offset=1000))
        result = analyze(self.root)
        self.assertEqual(result["possible_gtf_container_headers"], 0)
        self.assertEqual(result["gtf_header_rejected"], 1)

    def test_bad_version_one_bounds_is_rejected(self):
        self.put("bad.bin", fixture_v1(texture_bytes=1234))
        result = analyze(self.root)
        self.assertEqual(result["possible_gtf_container_headers"], 0)
        self.assertEqual(result["gtf_header_rejected"], 1)

    def test_bad_version_one_dimension_is_rejected(self):
        self.put("bad.bin", fixture_v1(dimension=3))
        result = analyze(self.root)
        self.assertEqual(result["gtf_header_rejected"], 1)

    def test_short_pretend_header_does_not_pass(self):
        self.put("small.bin", bytes.fromhex("02000101"))
        result = analyze(self.root)
        self.assertEqual(result["gtf_header_rejected"], 1)

    def test_dds_remains_stage290_only(self):
        self.put("v.dds", generated_dds((22, 44, 66, 255)))
        result = analyze(self.root)
        self.assertEqual(result["category_counts"]["classic_dds_deferred_to_stage290"], 1)
        self.assertEqual(result["possible_gtf_container_headers"], 0)

    def test_known_non_dds_image_is_not_gtf(self):
        self.put("image.png", b"\x89PNG\r\n\x1a\n" + bytes(64))
        result = analyze(self.root)
        self.assertEqual(result["category_counts"]["other_image_container_not_native_dds"], 1)

    def test_unknown_is_not_claimed_as_texture(self):
        self.put("blob.bin", b"not-a-texture")
        result = analyze(self.root)
        self.assertEqual(result["category_counts"]["unknown_or_non_texture"], 1)

    def test_file_limit_explicitly_reports_incomplete(self):
        self.put("a.bin", b"abc")
        self.put("b.bin", b"def")
        result = analyze(self.root, max_files=1)
        self.assertTrue(result["file_limit_reached"])
        self.assertFalse(result["scan_complete_within_file_limit"])
        self.assertEqual(result["files_scanned"], 1)

    def test_symlink_is_rejected(self):
        target = self.put("private.bin", b"file")
        (self.root / "alias.bin").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            analyze(self.root)

    def test_root_symlink_is_rejected(self):
        alias = self.root.parent / "link-root"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            analyze(alias)

    def test_cli_output_contains_only_aggregate_metadata(self):
        name = "never-leak-privately-owned-file.bin"
        self.put(name, fixture_v1())
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(["--extracted-root", str(self.root)])
        self.assertEqual(status, 0)
        self.assertEqual(stderr.getvalue(), "")
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["possible_gtf_container_headers"], 1)
        self.assertEqual(set(report["category_counts"]), set(CATEGORIES))
        self.assertNotIn(name, stdout.getvalue())
        self.assertNotIn(str(self.root), stdout.getvalue())
        self.assertNotIn("sha256", stdout.getvalue())

    def test_cli_failure_leaks_no_filename(self):
        target = self.put("secret-user-owned-resource.bin", b"plain")
        (self.root / "alias").symlink_to(target)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(["--extracted-root", str(self.root)])
        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn(target.name, stderr.getvalue())
        self.assertNotIn(str(self.root), stderr.getvalue())

    def test_invalid_file_budget_is_rejected(self):
        for limit in (0, 20001, True, -1):
            with self.assertRaises(ValueError):
                analyze(self.root, max_files=limit)

    def test_direct_prefix_contract_rejects_bad_types_and_bounds(self):
        with self.assertRaises(ValueError):
            classify_prefix(b"untrusted", 2)
        with self.assertRaises(ValueError):
            classify_prefix(bytearray(b"stuff"), 5)
        with self.assertRaises(ValueError):
            classify_prefix(bytes(PREFIX_BYTES + 1), PREFIX_BYTES + 1)


if __name__ == "__main__":
    unittest.main()
