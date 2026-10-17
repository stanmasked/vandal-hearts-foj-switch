"""Generated-only stage 158 benchmark correctness and privacy controls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stage158_benchmark import (
    PROFILES, benchmark, generated_case, generated_runs,
)
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import _candidate_runs


class Stage158BenchmarkTests(unittest.TestCase):
    def test_fixed_synthetic_case_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            left = folder / "first"
            right = folder / "second"
            a, a_prefix = generated_case(left, 32)
            b, b_prefix = generated_case(right, 32)
            self.assertEqual((a, a_prefix), (b, b_prefix))
            self.assertEqual((left / "generated.bin").read_bytes(),
                             (right / "generated.bin").read_bytes())
            self.assertNotIn(str(folder), json.dumps(a))

    def test_tiny_case_preserves_relation_and_table_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            source, prefix = generated_case(folder, 16)
            relations = build_relations(source, root=folder, prefix_bytes=prefix)
            self.assertEqual(relations["summary"]["dds_candidates"], 16)
            self.assertEqual(relations["summary"]["possible_pointer_matches"], 3)
            positions = [
                r["word_offset"]
                for c in relations["containers"][0]["candidates"]
                for r in c["possible_32bit_offset_references"]
            ]
            self.assertEqual(sorted(positions), [0, 4, 8])
            self.assertEqual(len(_candidate_runs(
                generated_runs(16), min_distinct=3)), 16)

    def test_smoke_benchmark_measures_two_workloads_across_two_sizes(self):
        report = benchmark(profile="smoke", repeats=1)
        self.assertEqual(report["schema"],
                         "foj-stage158-synthetic-performance-v1")
        self.assertEqual(report["profile"], "smoke")
        self.assertEqual(len(report["measurements"]), 4)
        self.assertEqual(
            [r["observed_records"] for r in report["measurements"]],
            [32, 32, 128, 128])
        for record in report["measurements"]:
            self.assertGreaterEqual(record["median_elapsed_ms"], 0)
            self.assertGreater(record["peak_traced_kib"], 0)
            self.assertIn(record["scenario"],
                          ("dds-prefix-relations", "hypothetical-table-runs"))

    def test_results_are_consistent_across_two_runs_not_timing(self):
        a = benchmark(profile="smoke", repeats=1)
        b = benchmark(profile="smoke", repeats=1)
        for previous, current in zip(a["measurements"], b["measurements"]):
            self.assertEqual(previous["scenario"], current["scenario"])
            self.assertEqual(previous["observed_records"],
                             current["observed_records"])
            self.assertEqual(previous.get("prefix_bytes"),
                             current.get("prefix_bytes"))

    def test_profile_definitions_are_bounded(self):
        self.assertEqual(PROFILES["smoke"], (32, 128))
        self.assertEqual(PROFILES["standard"], (128, 512))
        self.assertEqual(PROFILES["stress"], (512, 2048))
        for parameter in (
            {"profile": "unknown"}, {"repeats": 0}, {"repeats": 6},
            {"repeats": True},
        ):
            with self.subTest(parameter=parameter), self.assertRaises(ValueError):
                benchmark(**parameter)

    def test_input_size_and_group_boundaries_reject_invalid_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            for count in (0, -1, True, 2049):
                with self.subTest(count=count), self.assertRaises(ValueError):
                    generated_case(Path(tmp) / "case", count)
                with self.subTest(group=count), self.assertRaises(ValueError):
                    generated_runs(count)

    def test_cli_creates_json_without_private_paths_or_asset_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "performance.json"
            result = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage158_benchmark",
                 "--profile", "smoke", "--repeats", "1",
                 "--output", str(dest)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            published = dest.read_text(encoding="utf-8")
            data = json.loads(published)
            self.assertEqual(len(data["measurements"]), 4)
            self.assertNotIn(str(tmp), published)
            self.assertNotIn("DDS ", published)
            self.assertIn("Generated-only benchmark", result.stdout)
            self.assertFalse(data["original_foj_assets_verified"])
            self.assertFalse(data["switch_hardware_verified"])

    def test_cli_refuses_overwriting_existing_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "existing.json"
            dest.write_text("DO-NOT-OVERWRITE", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage158_benchmark",
                 "--output", str(dest)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(dest.read_text(encoding="utf-8"),
                             "DO-NOT-OVERWRITE")
            self.assertIn("new file", result.stderr)

    def test_cli_rejects_invalid_repeats_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "missing.json"
            result = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage158_benchmark",
                 "--repeats", "100", "--output", str(dest)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
