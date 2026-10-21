"""Stage294 synthetic tests: structural GTF-like hypotheses, no decoding."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.foj_stage292_synthetic_gtf_dds_roundtrip import generate_fixture
from tools.foj_stage294_owner_local_gtf_envelope import (
    READ_BYTES, MAX_SOURCE_BYTES, examine, examine_local, expected_contiguous_bytes,
    mip_shape, main,
)

def invented(width=64, height=64, mips=1, fmt=0xA5,
             corrupt_payload=0, trailer=b""):
    blob = bytearray(generate_fixture(width, height, mips, False))
    if fmt != 0xA5:
        shapes = mip_shape(width, height, mips)
        name = {0xA6:"bc1", 0xA7:"bc2", 0xA8:"bc3", 0x85:"rgba"}[fmt]
        if name == "rgba":
            data = blob[128:]
            pitch = width * 4
        else:
            data = bytes(expected_contiguous_bytes(shapes, name))
            pitch = ((width+3)//4)*(8 if name=="bc1" else 16)
        blob = bytearray(blob[:128] + data)
        struct.pack_into(">I", blob, 48, pitch)
        blob[36] = fmt
        struct.pack_into(">I", blob, 20, len(data))
    if corrupt_payload:
        struct.pack_into(">I", blob, 20, int.from_bytes(blob[20:24], "big") + corrupt_payload)
    return bytes(blob) + trailer


def header_check(blob):
    return examine(blob[:READ_BYTES], len(blob))


class Stage294GtfEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "owner"
        self.root.mkdir()

    def put(self, name, blob):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        return target

    def test_synthetic_one_mip_consistent_under_unverified_hypothesis(self):
        check = header_check(invented())
        self.assertEqual(check["decision"], "candidate_envelope_consistent_under_unverified_hypothesis")
        self.assertTrue(check["hypothetical_contiguous_envelope_match"])
        self.assertTrue(check["hypothetical_exact_file_extent"])
        self.assertTrue(check["hypothetical_base_pitch_match"])
        self.assertTrue(check["synthetic_fixture_marker_seen"])
        self.assertFalse(check["native_dds_conversion_authorized"])
        self.assertFalse(check["source_format_confirmed"])

    def test_three_mip_odd_height_contiguous_model(self):
        result = header_check(invented(24, 13, 3))
        self.assertTrue(result["possible_mip_chain"])
        self.assertTrue(result["hypothetical_exact_file_extent"])
        self.assertEqual(result["decision"], "candidate_envelope_consistent_under_unverified_hypothesis")

    def test_seven_level_chain(self):
        self.assertTrue(header_check(invented(64,64,7))["hypothetical_exact_file_extent"])

    def test_bc1_hypothesis_not_conversion(self):
        result = header_check(invented(fmt=0xA6))
        self.assertTrue(result["native_dds_format_subset_hint"])
        self.assertTrue(result["hypothetical_contiguous_envelope_match"])
        self.assertFalse(result["native_dds_conversion_authorized"])

    def test_bc3_hypothesis_not_conversion(self):
        result = header_check(invented(fmt=0xA8))
        self.assertTrue(result["hypothetical_base_pitch_match"])
        self.assertTrue(result["hypothetical_exact_file_extent"])

    def test_bc2_not_supported_by_current_native_loader(self):
        result = header_check(invented(fmt=0xA7))
        self.assertEqual(result["decision"], "bc2_unsupported_by_native_loader")
        self.assertFalse(result["native_dds_format_subset_hint"])

    def test_tiled_rgba_not_assumed_linear(self):
        result = header_check(invented(fmt=0x85))
        self.assertEqual(result["decision"], "nonlinear_layout_unverified")
        self.assertFalse(result["native_dds_conversion_authorized"])

    def test_extra_container_trailer_blocks_exact_extent(self):
        result = header_check(invented(trailer=b"container suffix"))
        self.assertFalse(result["hypothetical_exact_file_extent"])
        self.assertEqual(result["decision"], "candidate_storage_envelope_unresolved")

    def test_mismatching_payload_size_rejected(self):
        result = header_check(invented(corrupt_payload=-16))
        self.assertFalse(result["hypothetical_contiguous_envelope_match"])
        self.assertEqual(result["decision"], "candidate_storage_envelope_unresolved")

    def test_payload_exceeding_container_is_bad_header(self):
        result = header_check(invented(corrupt_payload=90000))
        self.assertIn(result["decision"], ("no_usable_source_layout_evidence",
                                            "inconsistent_candidate_header"))
        self.assertFalse(result["native_dds_conversion_authorized"])

    def test_wrong_base_pitch_does_not_match(self):
        b = bytearray(invented())
        struct.pack_into(">I", b, 48, 15)
        result = header_check(bytes(b))
        self.assertFalse(result["hypothetical_base_pitch_match"])
        self.assertEqual(result["decision"], "candidate_storage_envelope_unresolved")

    def test_mip_chain_exceeds_possible(self):
        b = bytearray(invented(8,1,1))
        b[37] = 16
        result = header_check(bytes(b))
        self.assertFalse(result["possible_mip_chain"])

    def test_unsupported_format_not_assumed(self):
        b = bytearray(invented())
        b[36] = 0x91
        result = header_check(bytes(b))
        self.assertEqual(result["decision"], "unclassified_gpu_format")

    def test_non_gtf_and_dds_never_claimed(self):
        self.assertFalse(header_check(bytes(128))["hypothetical_contiguous_envelope_match"])
        self.assertEqual(header_check(b"DDS "+bytes(124))["candidate_class"],
                         "classic_dds_deferred_to_stage290")

    def test_metadata_does_not_contain_source_dimensions_or_offsets(self):
        text = json.dumps(header_check(invented(24,13,3)), sort_keys=True)
        self.assertNotIn('"width"', text)
        self.assertNotIn('"height"', text)
        self.assertNotIn('"offset"', text)
        self.assertNotIn("sha256", text)
        self.assertNotIn("relative_path", text)

    def test_mip_shapes_and_bc_block_tail(self):
        self.assertEqual(mip_shape(8,4,3), ((8,4),(4,2),(2,1)))
        self.assertEqual(expected_contiguous_bytes(((8,4),(4,2),(2,1)), "bc1"), 16+8+8)
        self.assertEqual(expected_contiguous_bytes(((8,4),(4,2),(2,1)), "bc3"), 32+16+16)

    def test_invalid_mip_inputs_fail_closed(self):
        for args in ((8,4,0), (0,4,1), (8,0,1), (8,4,17),
                     (8,4,True), (16385,3,1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                mip_shape(*args)

    def test_invalid_prefix_or_file_limits_fail_closed(self):
        for p, size in ((b"X", 128), (bytes(129),129),
                        (bytes(128), MAX_SOURCE_BYTES+1),
                        (bytes(128),True), (bytearray(128),128)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                examine(p, size)

    def test_unknown_format_size_query_refused(self):
        with self.assertRaises(ValueError):
            expected_contiguous_bytes(((8,8),), "unknown")

    def test_owner_local_normal_file_contains_no_identifiers(self):
        secret = "private-original-asset-unique.bin"
        self.put("nested/"+secret, invented())
        result = examine_local(self.root, "nested/"+secret)
        self.assertTrue(result["hypothetical_contiguous_envelope_match"])
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_owner_local_source_symlink_refused(self):
        p = self.put("secret.bin", invented())
        (self.root/"alias.bin").symlink_to(p)
        with self.assertRaises(ValueError):
            examine_local(self.root, "alias.bin")

    def test_ancestor_symlink_refused(self):
        self.put("folder/data.bin", invented())
        (self.root/"alias").symlink_to(self.root/"folder",target_is_directory=True)
        with self.assertRaises(ValueError):
            examine_local(self.root, "alias/data.bin")

    def test_parent_path_escape_refused(self):
        self.put("safe.bin", invented())
        for name in ("../safe.bin","/tmp/test.bin","sub/../safe.bin"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                examine_local(self.root, name)

    def test_source_root_symlink_refused(self):
        self.put("safe.bin", invented())
        alias=self.root.parent/"symlink-root"
        alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):
            examine_local(alias, "safe.bin")

    def test_missing_file_never_falls_back(self):
        with self.assertRaises((ValueError, OSError)):
            examine_local(self.root, "missing.bin")

    def test_cli_prints_only_sanitized_metadata(self):
        source=self.put("secret-name.bin", invented())
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            rc=main(["--source-root",str(self.root),"--relative-file",source.name])
        self.assertEqual(rc,0)
        self.assertEqual(err.getvalue(),"")
        self.assertFalse(json.loads(out.getvalue())["native_dds_conversion_authorized"])
        self.assertNotIn(source.name,out.getvalue())
        self.assertNotIn(str(self.root),out.getvalue())

    def test_cli_refusal_never_leaks_path(self):
        target=self.put("secret-never-leak.bin",invented())
        (self.root/"alias").symlink_to(target)
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            rc=main(["--source-root",str(self.root),"--relative-file","alias"])
        self.assertEqual(rc,2)
        self.assertEqual(out.getvalue(),"")
        self.assertNotIn(target.name,err.getvalue())
        self.assertNotIn(str(self.root),err.getvalue())


if __name__=="__main__":
    unittest.main()
