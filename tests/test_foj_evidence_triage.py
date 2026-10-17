"""All evidence sources are derived from synthetic data, never FoJ PS3 files."""
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
from tools.foj_evidence_triage import triage_reports


def invented_dds():
    blob = bytearray(160)
    blob[:4] = b"DDS "
    for at, value in ((4, 124), (8, 0x81007), (12, 8), (16, 8),
                      (20, 32), (28, 1), (76, 32), (80, 4),
                      (84, 0x31545844), (108, 0x1000)):
        struct.pack_into("<I", blob, at, value)
    return blob


def fixture(root: Path, *, indices=(0, 1, 2, 3), decoy=False,
            endian="<"):
    buffer = bytearray(b"\xff" * 4096)
    targets = [1024, 1536, 2048, 2560]
    for at in targets:
        buffer[at:at + 160] = invented_dds()
    for i, target in enumerate(targets):
        struct.pack_into(endian + "I", buffer, 64 + 8 * i, target)
        struct.pack_into(endian + "I", buffer, 68 + 8 * i, indices[i])
    if decoy:
        for i in range(4):
            struct.pack_into(endian + "I", buffer, 3000 + 8 * i, i)
    (root / "synthetic.bin").write_bytes(buffer)
    layout = build_relations(inventory(root), root=root)
    tables = infer_tables(layout)
    indices_report = analyze_index_columns(tables, root=root)
    return layout, tables, indices_report


def first_row(triage):
    return triage["containers"][0]["table_observations"][0]


class CrossReportConsistencyTests(unittest.TestCase):
    def test_complete_synthetic_pipeline_is_only_internally_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources = fixture(Path(tmp))
            out = triage_reports(*sources)
            self.assertEqual(out["summary"]["tables_examined"], 1)
            self.assertEqual(
                first_row(out)["internal_triage"],
                "internally-consistent-for-private-review")
            self.assertEqual(first_row(out)["corroborated_pointer_rows"], 4)
            self.assertEqual(first_row(out)["reason_codes"], [])
            self.assertFalse(out["summary"]["foj_resource_format_confirmed"])
            self.assertFalse(first_row(out)["game_material_or_model_link_proven"])

    def test_big_endian_dense_permutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources = fixture(Path(tmp), endian=">", indices=(3, 0, 2, 1))
            out = triage_reports(*sources)
            self.assertEqual(first_row(out)["byte_order"], "big")
            self.assertEqual(
                first_row(out)["internal_triage"],
                "internally-consistent-for-private-review")

    def test_negative_control_and_absent_numeric_index_do_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources = fixture(Path(tmp), decoy=True)
            out = triage_reports(*sources)
            self.assertEqual(
                first_row(out)["internal_triage"], "insufficient-or-ambiguous")
            self.assertIn("similar-pattern-found-in-controls",
                          first_row(out)["reason_codes"])
            sources = fixture(Path(tmp), indices=(8, 9, 10, 11))
            out = triage_reports(*sources)
            self.assertEqual(first_row(out)["internal_triage"],
                             "insufficient-or-ambiguous")
            self.assertIn("no-secondary-index-pattern",
                          first_row(out)["reason_codes"])

    def test_missing_pointer_correspondence_is_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            layout, tables, indices = fixture(Path(tmp))
            layout["containers"][0]["candidates"][0][
                "possible_32bit_offset_references"].clear()
            out = triage_reports(layout, tables, indices)
            self.assertEqual(first_row(out)["internal_triage"],
                             "internally-contradicted")
            self.assertIn("pointer-hint-not-corroborated",
                          first_row(out)["reason_codes"])
            self.assertEqual(first_row(out)["corroborated_pointer_rows"], 3)

    def test_overlap_and_unknown_size_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            layout, tables, indices = fixture(Path(tmp))
            row = layout["containers"][0]["candidates"][0]
            row["candidate_span_end"] = 1537
            overlap = triage_reports(layout, tables, indices)
            self.assertIn("overlapping-dds-candidate-spans",
                          first_row(overlap)["reason_codes"])
            self.assertEqual(first_row(overlap)["internal_triage"],
                             "internally-contradicted")
            row["candidate_span_end"] = None
            missing = triage_reports(layout, tables, indices)
            self.assertIn("unknown-dds-payload-size",
                          first_row(missing)["reason_codes"])
            self.assertEqual(first_row(missing)["internal_triage"],
                             "insufficient-or-ambiguous")

    def test_missing_index_observation_and_unknown_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            layout, tables, indices = fixture(Path(tmp))
            indices["containers"] = []
            out = triage_reports(layout, tables, indices)
            self.assertIn("missing-index-observation",
                          first_row(out)["reason_codes"])
            # Stage-143 output naming a candidate that is absent from
            # stage-142 is a contradictory claim, not a valid relation.
            layout, tables, indices = fixture(Path(tmp))
            target = layout["containers"][0]["candidates"][0]["offset"]
            layout["containers"][0]["candidates"] = [
                row for row in layout["containers"][0]["candidates"]
                if row["offset"] != target
            ]
            out = triage_reports(layout, tables, indices)
            self.assertIn("missing-dds-header-candidate",
                          first_row(out)["reason_codes"])
            self.assertEqual(first_row(out)["internal_triage"],
                             "internally-contradicted")

    def test_mismatched_schema_filenames_duplicate_and_counts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            layout, tables, indices = fixture(Path(tmp))
            bad = copy.deepcopy(layout)
            bad["schema"] = "invented-other-schema"
            with self.assertRaises(ValueError):
                triage_reports(bad, tables, indices)
            bad = copy.deepcopy(tables)
            bad["containers"][0]["relative_path"] = "../unsafe"
            with self.assertRaises(ValueError):
                triage_reports(layout, bad, indices)
            bad = copy.deepcopy(tables)
            bad["containers"] *= 2
            with self.assertRaises(ValueError):
                triage_reports(layout, bad, indices)
            bad = copy.deepcopy(indices)
            bad["containers"][0]["examined_tables"][0]["entry_count"] = 5
            with self.assertRaises(ValueError):
                triage_reports(layout, tables, bad)
            bad = copy.deepcopy(tables)
            bad["containers"][0]["table_hypotheses"][0][
                "distinct_dds_targets"] = True
            with self.assertRaises(ValueError):
                triage_reports(layout, bad, indices)

    def test_no_candidate_input_and_malformed_control_counts(self):
        empty_layout = {
            "schema": "foj-texture-layout-hypotheses-v1",
            "pointer_scan": "first-file-prefix-aligned-uint32-le-be",
            "containers": [],
        }
        empty_tables = {
            "schema": "foj-resource-table-hypotheses-v1",
            "input_schema": "foj-texture-layout-hypotheses-v1",
            "containers": [],
        }
        empty_indices = {
            "schema": "foj-index-column-observations-v1",
            "source_schema": "foj-resource-table-hypotheses-v1",
            "containers": [],
        }
        out = triage_reports(empty_layout, empty_tables, empty_indices)
        self.assertEqual(out["summary"]["tables_examined"], 0)
        with tempfile.TemporaryDirectory() as tmp:
            layout, tables, indices = fixture(Path(tmp))
            bad = copy.deepcopy(indices)
            row = bad["containers"][0]["examined_tables"][0]
            row["independent_control_dense_windows"] = (
                row["independent_control_windows_checked"] + 1)
            with self.assertRaises(ValueError):
                triage_reports(layout, tables, bad)

    def test_cli_never_embeds_binary_or_absolute_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports = fixture(root)
            paths = [root / ("r" + str(i) + ".json") for i in range(3)]
            for path, report in zip(paths, reports):
                path.write_text(json.dumps(report), encoding="utf-8")
            out_path = root / "triage.json"
            invocation = [
                sys.executable, "-m", "tools.foj_evidence_triage",
                "--relations", str(paths[0]), "--tables", str(paths[1]),
                "--indices", str(paths[2]), "--output", str(out_path),
            ]
            cp = subprocess.run(invocation, capture_output=True, text=True,
                                check=True)
            self.assertIn("Cross-report tables checked: 1", cp.stdout)
            payload = out_path.read_text(encoding="utf-8")
            self.assertNotIn(str(root), payload)
            self.assertNotIn("DDS ", payload)
            self.assertFalse(json.loads(payload)["summary"][
                "foj_resource_format_confirmed"])


if __name__ == "__main__":
    unittest.main()
