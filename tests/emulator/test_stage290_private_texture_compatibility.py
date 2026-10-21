"""Stage290 synthetic-only safety and native DDS compatibility regressions."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage290_private_texture_compatibility import analyze, main

COLOR = (48, 79, 118, 255)


def _dds_rgba(*, alpha: int = 255, bgra: bool = False) -> bytes:
    blob = bytearray(generated_dds((COLOR[0], COLOR[1], COLOR[2], alpha)))
    if bgra:
        struct.pack_into("<I", blob, 92, 0x00FF0000)
        struct.pack_into("<I", blob, 100, 0x000000FF)
    return bytes(blob)


def _dds_bc(fourcc: bytes) -> bytes:
    width = height = 64
    block = 8 if fourcc == b"DXT1" else 16
    base_bytes = (width // 4) * (height // 4) * block
    header = bytearray(128)
    header[:4] = b"DDS "
    for offset, value in (
        (4, 124), (8, 0x81007), (12, height), (16, width),
        (20, base_bytes), (76, 32), (80, 4),
        (84, int.from_bytes(fourcc, "little")), (108, 0x1000),
    ):
        struct.pack_into("<I", header, offset, value)
    return bytes(header) + bytes(base_bytes)


class Stage290PrivateSourceTriageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "extracted"
        self.root.mkdir()

    def put(self, relative: str, data: bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(data)
        return path

    def test_no_signatures_is_complete_but_does_not_verify_ps3_format(self):
        self.put("random.bin", b"not a DDS")
        result = analyze(self.root)
        self.assertTrue(result["scan_complete_within_declared_limits"])
        self.assertEqual(result["dds_headers_seen"], 0)
        self.assertFalse(result["original_ps3_format_verified"])
        self.assertFalse(result["original_game_ready_to_render"])

    def test_rgba_front_and_opaque_rear_eligibility(self):
        self.put("set/alpha.dds", _dds_rgba())
        result = analyze(self.root)
        self.assertEqual(result["exact_native_dds_compatible"], 1)
        self.assertEqual(result["native_format_counts"]["RGBA8"], 1)
        self.assertEqual(result["opaque_rear_compatible_candidates"], 1)
        self.assertFalse(result["original_material_mapping_verified"])

    def test_bgra_masks_match_native_loader(self):
        self.put("bgra.dds", _dds_rgba(bgra=True))
        result = analyze(self.root)
        self.assertEqual(result["native_format_counts"]["BGRA8"], 1)
        self.assertEqual(result["opaque_rear_compatible_candidates"], 1)

    def test_translucent_raw_never_eligible_for_opaque_rear(self):
        self.put("rgba.dds", _dds_rgba(alpha=128))
        result = analyze(self.root)
        self.assertEqual(result["exact_native_dds_compatible"], 1)
        self.assertEqual(result["opaque_rear_compatible_candidates"], 0)

    def test_bc1_and_bc3_valid_front_but_not_opaque_rear(self):
        self.put("bc1.dds", _dds_bc(b"DXT1"))
        self.put("bc3.dds", _dds_bc(b"DXT5"))
        result = analyze(self.root)
        self.assertEqual(result["exact_native_dds_compatible"], 2)
        self.assertEqual(result["native_format_counts"]["BC1/DXT1"], 1)
        self.assertEqual(result["native_format_counts"]["BC3/DXT5"], 1)
        self.assertEqual(result["opaque_rear_compatible_candidates"], 0)

    def test_embedded_header_is_never_a_native_compatible_file(self):
        self.put("packed.bin", b"synthetic prefix!" + _dds_rgba())
        result = analyze(self.root)
        self.assertEqual(result["embedded_dds_headers_not_native_inputs"], 1)
        self.assertEqual(result["exact_native_dds_compatible"], 0)
        self.assertEqual(result["file_start_dds_candidates"], 0)

    def test_shallow_dds_that_native_rejects_counted_incompatible(self):
        bad = bytearray(_dds_rgba())
        struct.pack_into("<I", bad, 108, 0)
        self.put("unsupported_caps.dds", bytes(bad))
        result = analyze(self.root)
        self.assertEqual(result["file_start_dds_candidates"], 1)
        self.assertEqual(result["exact_native_dds_compatible"], 0)
        self.assertEqual(result["exact_native_dds_incompatible"], 1)

    def test_extra_trailing_bytes_rejected_by_exact_native_validator(self):
        self.put("trailer.dds", _dds_rgba() + b"not part of DDS")
        result = analyze(self.root)
        self.assertEqual(result["exact_native_dds_incompatible"], 1)
        self.assertEqual(result["opaque_rear_compatible_candidates"], 0)

    def test_large_file_skip_is_reported_incomplete_not_no_assets(self):
        self.put("large.bin", b"x" * (1024 * 1024 + 1))
        result = analyze(self.root, max_file_mib=1)
        self.assertEqual(result["skipped_large_files"], 1)
        self.assertFalse(result["scan_complete_within_declared_limits"])

    def test_reaching_scan_file_limit_is_explicitly_incomplete(self):
        self.put("one.bin", b"plain")
        self.put("two.bin", b"plain")
        result = analyze(self.root, max_files=1)
        self.assertTrue(result["file_limit_reached"])
        self.assertFalse(result["scan_complete_within_declared_limits"])

    def test_symlinked_file_fails_closed(self):
        original = self.put("good.dds", _dds_rgba())
        (self.root / "linked.dds").symlink_to(original)
        with self.assertRaisesRegex(ValueError, "linked or special"):
            analyze(self.root)

    def test_symlinked_source_directory_fails_closed(self):
        alias = self.root.parent / "link-root"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            analyze(alias)

    def test_cli_never_prints_private_filename_or_bytes(self):
        secret_name = "personal-game-resource-unique.dds"
        self.put(secret_name, _dds_rgba())
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            status = main(["--extracted-root", str(self.root)])
        self.assertEqual(status, 0)
        data = output.getvalue()
        self.assertEqual(error.getvalue(), "")
        self.assertNotIn(secret_name, data)
        self.assertNotIn(str(self.root), data)
        self.assertNotIn("sha256", data)
        parsed = json.loads(data)
        self.assertEqual(parsed["exact_native_dds_compatible"], 1)

    def test_cli_rejection_does_not_leak_private_filename(self):
        secret = "private-original-game.pkg"
        target = self.put(secret, b"not a DDS")
        (self.root / "alias").symlink_to(target)
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            status = main(["--extracted-root", str(self.root)])
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn(secret, error.getvalue())
        self.assertNotIn(str(self.root), error.getvalue())

    def test_invalid_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze(self.root, max_file_mib=513)
        with self.assertRaises(ValueError):
            analyze(self.root, max_files=0)


if __name__ == "__main__":
    unittest.main()
