"""Corrupt/incomplete invented DDS only; no original PS3 resources."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.foj_corrupt_container_matrix import (
    CASES, DDS_BASE, DDS_SPACING, DDS_SIZE, FILE_BYTES,
    SPEC, _mutate, run_corruption_matrix,
)
from tools.foj_stability_matrix import synthetic_sample, pipeline
from tools.foj_texture_probe import inventory
from tools.foj_texture_relations import build_relations


class CorruptContainerTests(unittest.TestCase):
    def test_expected_synthetic_mutations(self):
        result = run_corruption_matrix()
        self.assertEqual(result["summary"]["cases"], len(CASES))
        self.assertEqual(result["summary"]["unexpected"], 0)
        self.assertEqual(result["summary"]["matched_expectations"], len(CASES))
        self.assertFalse(result["original_foj_asset_verified"])
        self.assertTrue(all(c["matches_expectation"] for c in result["cases"]))

    def test_runs_are_deterministic(self):
        self.assertEqual(run_corruption_matrix(), run_corruption_matrix())

    def test_truncated_payload_is_a_hard_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            synthetic_sample(root, SPEC)
            file = root / "synthetic.bin"
            file.write_bytes(_mutate(file.read_bytes(), "truncated-last-image"))
            manifest = inventory(root)
            self.assertEqual(len(manifest["candidates"]), 4)
            self.assertEqual(manifest["candidates"][-1]["payload_check"], "truncated")
            layout = build_relations(manifest, root=root)
            self.assertEqual(layout["containers"][0]["candidates"][-1][
                "payload_check"], "truncated")
            result = pipeline(root)
            self.assertEqual(result["summary"]["internally_contradicted"], 1)
            self.assertIn("dds-payload-truncated", result["containers"][0][
                "table_observations"][0]["reason_codes"])

    def test_missing_pointer_breaks_table_without_inventing_a_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            synthetic_sample(root, SPEC)
            path = root / "synthetic.bin"
            path.write_bytes(_mutate(path.read_bytes(), "pointer-gap"))
            self.assertEqual(len(inventory(root)["candidates"]), 4)
            out = pipeline(root)
            self.assertEqual(out["summary"]["tables_examined"], 0)

    def test_partial_dds_header_is_not_classified_as_texture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            synthetic_sample(root, SPEC)
            f = root / "synthetic.bin"
            f.write_bytes(_mutate(f.read_bytes(), "partial-header-at-end"))
            self.assertEqual(len(inventory(root)["candidates"]), 3)

    def test_misaligned_embedded_header_can_still_be_a_valid_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            synthetic_sample(root, SPEC)
            f = root / "synthetic.bin"
            f.write_bytes(_mutate(f.read_bytes(), "unaligned-embedded-dds"))
            offsets = [x["offset"] for x in inventory(root)["candidates"]]
            self.assertIn(DDS_BASE + 3*DDS_SPACING + 1, offsets)
            result = pipeline(root)
            self.assertEqual(
                result["summary"]["internally_consistent_for_private_review"], 1)

    def test_metadata_preserves_only_defined_payload_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            synthetic_sample(root, SPEC)
            manifest = inventory(root)
            manifest["candidates"][0]["payload_check"] = "invented"
            with self.assertRaises(ValueError):
                build_relations(manifest, root=root)

    def test_unknown_fourcc_is_not_treated_as_proven_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "synthetic"
            synthetic_sample(root, SPEC)
            f = root / "synthetic.bin"
            f.write_bytes(_mutate(f.read_bytes(), "unknown-fourcc"))
            report = pipeline(root)
            self.assertEqual(report["summary"]["insufficient_or_ambiguous"], 1)
            reasons = report["containers"][0]["table_observations"][0]["reason_codes"]
            self.assertIn("unknown-dds-payload-size", reasons)

    def test_unexpected_label_is_detected(self):
        item = list(CASES[:1])
        name, expected, count = item[0]
        item[0] = name, "wrong-on-purpose", count
        report = run_corruption_matrix(tuple(item))
        self.assertEqual(report["summary"]["unexpected"], 1)
        self.assertEqual(report["cases"][0]["actual_observation"],
                         "internally-consistent-for-private-review")

    def test_invalid_matrix_parameters_rejected(self):
        with self.assertRaises(ValueError):
            run_corruption_matrix(())
        with self.assertRaises(ValueError):
            run_corruption_matrix(CASES * 3)
        with self.assertRaises(ValueError):
            run_corruption_matrix(CASES[:1] + CASES[:1])
        with self.assertRaises(ValueError):
            run_corruption_matrix((("does-not-exist", "none", 0),))

    def test_cli_aggregates_no_source_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "matrix.json"
            res = subprocess.run(
                [sys.executable, "-m", "tools.foj_corrupt_container_matrix",
                 "--output", str(output)],
                text=True, capture_output=True, check=True)
            self.assertIn("regressions: 0", res.stdout)
            content = output.read_text(encoding="utf-8")
            self.assertNotIn(str(tmp), content)
            self.assertNotIn("synthetic.bin", content)
            # Human-readable DDS format names are fine; raw binary or
            # embedded source paths must never appear in the report.
            self.assertNotIn("\\u0000", content)
            self.assertFalse(json.loads(content)["original_foj_asset_verified"])


if __name__ == "__main__":
    unittest.main()
