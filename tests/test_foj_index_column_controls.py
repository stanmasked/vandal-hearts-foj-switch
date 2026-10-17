"""Invented data only: dense numeric patterns are not FoJ material IDs."""
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.foj_texture_probe import inventory
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import infer_tables
from tools.foj_index_column_controls import analyze_index_columns


def make_dds():
    buf = bytearray(160)
    buf[:4] = b"DDS "
    for pos, value in [(4, 124), (8, 0x81007), (12, 8), (16, 8),
                       (20, 32), (28, 1), (76, 32), (80, 4),
                       (84, 0x31545844), (108, 0x1000)]:
        struct.pack_into("<I", buf, pos, value)
    return bytes(buf)


def synthetic_container(root, *, order="little", indices=(0, 1, 2, 3),
                        decoy=False, stride=8):
    raw = bytearray(b"\xff" * 4096)
    targets = (1024, 1536, 2048, 2560)
    for dest in targets:
        raw[dest:dest + 160] = make_dds()
    for i, dest in enumerate(targets):
        pos = 64 + i * stride
        raw[pos:pos + 4] = dest.to_bytes(4, order)
        raw[pos + 4:pos + 8] = indices[i].to_bytes(4, order)
    if decoy:
        for i in range(4):
            pos = 3000 + i * stride
            raw[pos:pos + 4] = i.to_bytes(4, order)
    (root / "invented.bin").write_bytes(raw)
    return root


def table_report(root):
    return infer_tables(build_relations(inventory(root), root=root))


class IndexColumnControlTests(unittest.TestCase):
    def test_complete_pipeline_little_endian(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_container(Path(tmp))
            table = table_report(root)
            self.assertEqual(table["summary"]["table_hypotheses"], 1)
            result = analyze_index_columns(table, root=root, prefix_bytes=4096)
            self.assertEqual(result["summary"]["index_like_single_field"], 1)
            self.assertFalse(result["summary"]["model_or_material_mapping_verified"])
            item = result["containers"][0]["examined_tables"][0]
            self.assertEqual(item["structural_observation"], "index-like-unverified")
            self.assertEqual(item["possible_secondary_index_fields"], [{
                "field_delta_from_pointer_bytes": 4,
                "pattern": "ascending-zero-based",
                "distinct_numeric_values": 4,
            }])
            self.assertNotIn(str(root), json.dumps(result))

    def test_big_endian_permuted_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_container(Path(tmp), order="big",
                                       indices=(2, 0, 3, 1))
            result = analyze_index_columns(table_report(root), root=root)
            item = result["containers"][0]["examined_tables"][0]
            self.assertEqual(item["byte_order"], "big")
            self.assertEqual(item["possible_secondary_index_fields"][0][
                "pattern"], "zero-based-permutation")

    def test_repeated_and_out_of_range_are_not_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_container(Path(tmp), indices=(0, 0, 0, 0))
            output = analyze_index_columns(table_report(root), root=root)
            item = output["containers"][0]["examined_tables"][0]
            self.assertEqual(item["structural_observation"], "no-index-like-field")
            root = synthetic_container(Path(tmp), indices=(20, 21, 22, 23))
            output = analyze_index_columns(table_report(root), root=root)
            self.assertEqual(output["summary"]["index_like_single_field"], 0)

    def test_decoy_window_warns_about_false_coincidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_container(Path(tmp), decoy=True)
            out = analyze_index_columns(table_report(root), root=root,
                                        prefix_bytes=4096,
                                        max_control_windows=1024)
            item = out["containers"][0]["examined_tables"][0]
            self.assertEqual(item["structural_observation"],
                             "index-like-with-control-matches")
            self.assertGreaterEqual(item["independent_control_dense_windows"], 1)
            self.assertGreater(item["independent_control_windows_checked"], 0)
            self.assertEqual(out["summary"]["index_like_with_control_matches"], 1)

    def test_stride_four_cannot_contain_secondary_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blob = bytearray(b"\xff" * 4096)
            for i, off in enumerate((1024, 1536, 2048, 2560)):
                blob[off:off + 160] = make_dds()
                struct.pack_into("<I", blob, i * 4, off)
            (root / "invented.bin").write_bytes(blob)
            result = analyze_index_columns(table_report(root), root=root)
            item = result["containers"][0]["examined_tables"][0]
            self.assertEqual(item["structural_observation"], "not-eligible")
            self.assertEqual(item["possible_secondary_index_fields"], [])

    def test_metadata_rejection_and_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_container(Path(tmp))
            report = table_report(root)
            with self.assertRaises(ValueError):
                analyze_index_columns(report, root=root, prefix_bytes=3)
            with self.assertRaises(ValueError):
                analyze_index_columns(report, root=root, min_entries=2)
            with self.assertRaises(ValueError):
                analyze_index_columns(report, root=root, max_control_windows=0)
            for key, invalid in (
                ("stride_bytes", 7), ("entry_count", 0),
                ("end_word_offset", 10), ("byte_order", "middle"),
                ("target_dds_offsets", [1024]),
                ("distinct_dds_targets", 17),
            ):
                bad = copy.deepcopy(report)
                bad["containers"][0]["table_hypotheses"][0][key] = invalid
                with self.subTest(key=key), self.assertRaises(ValueError):
                    analyze_index_columns(bad, root=root)
            bad = copy.deepcopy(report)
            bad["containers"][0]["relative_path"] = "../outside"
            with self.assertRaises(ValueError):
                analyze_index_columns(bad, root=root)
            bad = copy.deepcopy(report)
            bad["schema"] = "unknown"
            with self.assertRaises(ValueError):
                analyze_index_columns(bad, root=root)

    def test_symlink_and_empty_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_container(Path(tmp))
            source = table_report(root)
            (root / "link.bin").symlink_to(root / "invented.bin")
            bad = copy.deepcopy(source)
            bad["containers"][0]["relative_path"] = "link.bin"
            with self.assertRaises(ValueError):
                analyze_index_columns(bad, root=root)
            # Tiny prefix still supports the four pointer words, but does not
            # offer a comparable independent control window.
            result = analyze_index_columns(source, root=root, prefix_bytes=96)
            item = result["containers"][0]["examined_tables"][0]
            self.assertEqual(item["independent_control_dense_windows"], 0)
            self.assertEqual(item["structural_observation"], "index-like-unverified")

    def test_cli_no_pixels_or_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = synthetic_container(Path(tmp))
            source, output = root / "tables.json", root / "index-hints.json"
            source.write_text(json.dumps(table_report(root)), encoding="utf-8")
            p = subprocess.run(
                [sys.executable, "-m", "tools.foj_index_column_controls",
                 str(source), "--root", str(root), "--output", str(output)],
                check=True, text=True, capture_output=True)
            self.assertIn("index-like single-field observations: 1", p.stdout)
            payload = output.read_text(encoding="utf-8")
            self.assertNotIn(str(root), payload)
            self.assertNotIn("DDS ", payload)
            self.assertFalse(json.loads(payload)["summary"][
                "model_or_material_mapping_verified"])


if __name__ == "__main__":
    unittest.main()
