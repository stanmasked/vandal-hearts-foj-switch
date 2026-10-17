"""Deterministic generated DDS stress cases; never original FoJ game assets."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stability_matrix import (
    CASES, FILE_BYTES, pipeline, run_stability_matrix, synthetic_sample,
)


class SyntheticMatrixTests(unittest.TestCase):
    def test_all_predetermined_variants(self):
        result = run_stability_matrix()
        self.assertEqual(result["summary"]["total_cases"], len(CASES))
        self.assertEqual(result["summary"]["unexpected_cases"], 0)
        self.assertEqual(result["summary"]["matched_expectations"], len(CASES))
        self.assertFalse(result["game_format_verified"])
        for row in result["cases"]:
            self.assertTrue(row["matches_expectation"])
            self.assertEqual(row["baseline_tables"], 1)
            self.assertEqual(row["holdout_tables"], 1)

    def test_same_matrix_repeats_bit_for_bit(self):
        a = run_stability_matrix()
        b = run_stability_matrix()
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))

    def test_single_scenario_and_expected_regression_are_reported(self):
        one = run_stability_matrix(CASES[:1])
        self.assertEqual(one["summary"]["total_cases"], 1)
        mutated = list(CASES[:1])
        name, base, holdout, _ = mutated[0]
        mutated[0] = name, base, holdout, "incorrect-test-expectation"
        result = run_stability_matrix(tuple(mutated))
        self.assertEqual(result["summary"]["unexpected_cases"], 1)
        self.assertFalse(result["cases"][0]["matches_expectation"])
        self.assertEqual(result["cases"][0]["actual_observation"],
                         "repeated-unverified-pattern")

    def test_short_table_reports_insufficient_evidence(self):
        one = run_stability_matrix(
            tuple(c for c in CASES if c[0] == "short-tables"))
        self.assertEqual(one["cases"][0]["actual_observation"],
                         "insufficient-consistent-occurrences")

    def test_control_decoy_is_caught(self):
        one = run_stability_matrix(
            tuple(c for c in CASES if c[0] == "negative-control-decoy"))
        self.assertEqual(one["cases"][0]["actual_observation"],
                         "holdout-ambiguous")

    def test_bad_synthetic_parameters_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = (
                (2, 8, "little", "ascending", False),
                (9, 8, "little", "ascending", False),
                (4, 4, "little", "ascending", False),
                (4, 8, "middle", "ascending", False),
                (4, 8, "little", "unknown", False),
                (4, 8, "little", "ascending", 1),
            )
            for spec in invalid:
                with self.subTest(spec=spec), self.assertRaises(ValueError):
                    synthetic_sample(root / "invalid", spec)
            self.assertFalse((root / "invalid").exists())

    def test_binary_fixtures_are_generated_and_only_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dataset"
            synthetic_sample(root, (4, 8, "big", "ascending", False))
            path = root / "synthetic.bin"
            self.assertEqual(path.stat().st_size, FILE_BYTES)
            self.assertEqual(path.read_bytes()[2048:2052], b"DDS ")
            output = pipeline(root)
            self.assertEqual(output["summary"]["tables_examined"], 1)
            self.assertFalse(output["summary"]["foj_resource_format_confirmed"])

    def test_invalid_matrix_requests_rejected(self):
        with self.assertRaises(ValueError):
            run_stability_matrix(())
        with self.assertRaises(ValueError):
            run_stability_matrix(tuple(CASES) * 5)
        with self.assertRaises(ValueError):
            run_stability_matrix(CASES[:1] + CASES[:1])

    def test_cli_does_not_expose_bytes_or_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "local-report.json"
            cmd = [
                sys.executable, "-m", "tools.foj_stability_matrix",
                "--output", str(output),
            ]
            cp = subprocess.run(cmd, text=True, capture_output=True,
                                check=True)
            self.assertIn("regressions: 0", cp.stdout)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["summary"]["unexpected_cases"], 0)
            content = output.read_text(encoding="utf-8")
            self.assertNotIn(str(tmp), content)
            self.assertNotIn("DDS ", content)
            self.assertNotIn("synthetic.bin", content)
            self.assertFalse(result["game_format_verified"])


if __name__ == "__main__":
    unittest.main()
