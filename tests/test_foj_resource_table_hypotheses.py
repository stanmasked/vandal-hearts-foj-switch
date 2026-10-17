"""Synthetic-only validation of possible pointer tables; no FoJ game data."""
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


def make_dds():
    buf = bytearray(160)
    buf[:4] = b"DDS "
    for pos, val in [(4, 124), (8, 0x81007), (12, 8), (16, 8),
                     (20, 32), (28, 1), (76, 32), (80, 4),
                     (84, 0x31545844), (108, 0x1000)]:
        struct.pack_into("<I", buf, pos, val)
    return bytes(buf)


def generated_report(root):
    return build_relations(inventory(root), root=root)


def fake_report(entries, *, path="invented.bin", prefix=65536):
    """entries: (dds_target, word_offset, endian) metadata only."""
    by_target = {}
    for target, word, endian in entries:
        by_target.setdefault(target, []).append({
            "word_offset": word, "byte_order": endian,
            "interpretation": "possible-file-relative-offset"})
    return {
        "schema": "foj-texture-layout-hypotheses-v1",
        "pointer_scan": "first-file-prefix-aligned-uint32-le-be",
        "pointer_prefix_bytes": prefix,
        "containers": [{
            "relative_path": path,
            "candidates": [
                {"offset": target,
                 "possible_32bit_offset_references": refs}
                for target, refs in sorted(by_target.items())
            ]
        }]
    }


class TableHypothesisTests(unittest.TestCase):
    def test_real_pipeline_synthetic_endian_and_strides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = bytearray(b"\xff" * 4096)
            dds = make_dds()
            for offset in (512, 1024, 1536, 2048, 2560, 3072):
                data[offset:offset + len(dds)] = dds
            for word, dest in ((0, 512), (4, 1024), (8, 1536)):
                struct.pack_into("<I", data, word, dest)
            for word, dest in ((64, 2048), (72, 2560), (80, 3072)):
                struct.pack_into(">I", data, word, dest)
            # False positive "pointer" in DDS data; stage 142 excludes it.
            struct.pack_into("<I", data, 512 + 140, 512)
            (root / "pack.bin").write_bytes(data)
            metadata = generated_report(root)
            self.assertEqual(len(metadata["containers"][0]["candidates"]), 6)
            output = infer_tables(metadata)
            self.assertEqual(output["summary"]["table_hypotheses"], 2)
            self.assertTrue(output["summary"]["no_model_or_material_mapping_established"])
            tables = output["containers"][0]["table_hypotheses"]
            self.assertEqual([(t["start_word_offset"], t["stride_bytes"],
                               t["byte_order"], t["entry_count"]) for t in tables],
                             [(0, 4, "little", 3), (64, 8, "big", 3)])
            self.assertEqual(tables[0]["target_dds_offsets"], [512, 1024, 1536])
            self.assertEqual(tables[1]["target_dds_offsets"], [2048, 2560, 3072])
            self.assertNotIn(str(root), json.dumps(output))

    def test_short_or_repeated_references_not_tables(self):
        report = fake_report([
            (512, 0, "little"), (512, 4, "little"),
            (512, 8, "little"), (1024, 80, "little"),
        ])
        self.assertEqual(infer_tables(report)["summary"]["table_hypotheses"], 0)
        report = fake_report([(512, 0, "little"), (1024, 4, "little")])
        self.assertEqual(infer_tables(report)["summary"]["table_hypotheses"], 0)
        result = infer_tables(report, min_distinct=2)
        self.assertEqual(result["summary"]["table_hypotheses"], 1)
        self.assertEqual(result["containers"][0]["table_hypotheses"][0][
            "target_dds_offsets"], [512, 1024])

    def test_subsampled_alternate_strides_are_suppressed(self):
        report = fake_report([(512, 0, "little"), (768, 4, "little"),
                              (1024, 8, "little"), (1280, 12, "little"),
                              (1536, 16, "little")])
        output = infer_tables(report)
        tables = output["containers"][0]["table_hypotheses"]
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["stride_bytes"], 4)
        self.assertEqual(tables[0]["entry_count"], 5)

    def test_ambiguous_word_offset_rejected(self):
        report = fake_report([
            (512, 0, "little"), (768, 0, "little"),
            (1024, 4, "little"), (1280, 8, "little")])
        self.assertEqual(infer_tables(report)["summary"]["table_hypotheses"], 0)

    def test_invalid_json_and_path_shapes_are_rejected(self):
        report = fake_report([(512, 0, "little"), (768, 4, "little"),
                              (1024, 8, "little")])
        bad_cases = []
        x = json.loads(json.dumps(report)); x["schema"] = "other"; bad_cases.append(x)
        x = json.loads(json.dumps(report)); x["pointer_scan"] = "disabled"; bad_cases.append(x)
        x = json.loads(json.dumps(report)); x["pointer_prefix_bytes"] = 0; bad_cases.append(x)
        x = json.loads(json.dumps(report)); x["containers"][0]["relative_path"] = "../escape"; bad_cases.append(x)
        x = json.loads(json.dumps(report)); x["containers"][0]["candidates"][0]["offset"] = -1; bad_cases.append(x)
        x = json.loads(json.dumps(report)); x["containers"][0]["candidates"][0][
            "possible_32bit_offset_references"][0]["word_offset"] = 3; bad_cases.append(x)
        x = json.loads(json.dumps(report)); x["containers"][0]["candidates"][0][
            "possible_32bit_offset_references"][0]["byte_order"] = "middle"; bad_cases.append(x)
        x = json.loads(json.dumps(report)); x["containers"][0]["candidates"][0][
            "possible_32bit_offset_references"][0]["word_offset"] = 65536; bad_cases.append(x)
        for bad in bad_cases:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    infer_tables(bad)
        with self.assertRaises(ValueError):
            infer_tables(report, max_tables=0)
        with self.assertRaises(ValueError):
            infer_tables(report, min_distinct=1)

    def test_table_budget_and_independent_files(self):
        report = fake_report([(512, 0, "little"), (768, 4, "little"),
                              (1024, 8, "little")], path="z.bin")
        report["containers"].append(fake_report([
            (2048, 64, "big"), (2560, 68, "big"),
            (3072, 72, "big")], path="a.bin")["containers"][0])
        output = infer_tables(report)
        self.assertEqual([c["relative_path"] for c in output["containers"]],
                         ["a.bin", "z.bin"])
        self.assertEqual(output["summary"]["table_hypotheses"], 2)
        with self.assertRaises(ValueError):
            infer_tables(report, max_tables=1)

    def test_cli_is_metadata_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = fake_report([(512, 0, "little"), (768, 4, "little"),
                                (1024, 8, "little")], path="PRIVATE_SYNTHETIC.bin")
            source = root / "input.json"
            output = root / "output.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            cp = subprocess.run(
                [sys.executable, "-m", "tools.foj_resource_table_hypotheses",
                 str(source), "--output", str(output)],
                check=True, capture_output=True, text=True)
            self.assertIn("Hypothetical pointer tables: 1", cp.stdout)
            text = output.read_text(encoding="utf-8")
            self.assertNotIn(str(root), text)
            self.assertEqual(json.loads(text)["summary"]["table_hypotheses"], 1)


if __name__ == "__main__":
    unittest.main()
