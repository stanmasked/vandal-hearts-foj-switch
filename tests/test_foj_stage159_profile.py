"""Stage 159 tests exercise generated-only profiling, without user assets."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import tools.foj_stage159_profile as profiler
from tools.foj_stage158_benchmark import PROFILES
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import infer_tables


class SyntheticHotspotProfileTests(unittest.TestCase):
    def test_generated_table_manifest_is_deterministic_and_private(self):
        first = profiler.generated_table_manifest(32)
        second = profiler.generated_table_manifest(32)
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "foj-texture-layout-hypotheses-v1")
        self.assertEqual(len(first["containers"][0]["candidates"]), 96)
        self.assertEqual(infer_tables(first)["summary"]["table_hypotheses"], 32)
        self.assertNotIn("/tmp/", json.dumps(first))

    def test_smoke_has_four_complete_recorded_workloads(self):
        result = profiler.profile_synthetic(profile="smoke", repeats=1)
        self.assertEqual(result["schema"], "foj-stage159-synthetic-hotspots-v1")
        self.assertEqual(result["profile"], "smoke")
        self.assertEqual([x["observed_records"] for x in result["observations"]],
                         [32, 32, 128, 128])
        self.assertFalse(result["original_foj_assets_verified"])
        self.assertFalse(result["switch_hardware_verified"])
        for row in result["observations"]:
            self.assertGreaterEqual(row["median_wall_elapsed_ms"], 0)
            self.assertGreaterEqual(row["median_profiled_cpu_ms"], 0)
            self.assertTrue(row["phases"])
            self.assertLessEqual(len(row["phases"]), profiler.MAX_PHASES)
            for phase in row["phases"]:
                self.assertIn(phase["phase"],
                              set(profiler.SAFE_PHASES[row["scenario"]].values()))
                self.assertGreater(phase["total_calls"], 0)
                self.assertGreaterEqual(phase["median_cumulative_cpu_ms"], 0)
                self.assertGreaterEqual(phase["median_self_cpu_ms"], 0)

    def test_profiled_functions_include_real_phase_boundaries(self):
        result = profiler.profile_synthetic(profile="smoke")
        expected = [
            ("relation-analysis", "dds-range-index", "json-budget-check"),
            ("table-analysis", "table-run-search", "pointer-validation"),
        ]
        for row, names in zip(result["observations"][:2], expected):
            present = {x["phase"] for x in row["phases"]}
            self.assertTrue(set(names).issubset(present), (names, present))

    def test_repeats_do_not_change_counts_or_safe_labels(self):
        first = profiler.profile_synthetic(profile="smoke", repeats=1)
        second = profiler.profile_synthetic(profile="smoke", repeats=2)
        for original, repeated in zip(first["observations"],
                                      second["observations"]):
            self.assertEqual(original["observed_records"],
                             repeated["observed_records"])
            self.assertEqual({p["phase"] for p in original["phases"]},
                             {p["phase"] for p in repeated["phases"]})

    def test_limits_reject_bool_excess_and_unknown_profile(self):
        invalid = (
            {"profile": "unknown"}, {"repeats": True},
            {"repeats": 0}, {"repeats": 4},
            {"top_phases": 0}, {"top_phases": False},
            {"top_phases": 9},
        )
        for setting in invalid:
            with self.subTest(setting=setting), self.assertRaisesRegex(
                    ValueError, "Invalid synthetic profiling configuration"):
                profiler.profile_synthetic(**setting)

    def test_filtered_phases_do_not_reveal_raw_profiler_locations(self):
        report = profiler.profile_synthetic(profile="smoke")
        output = json.dumps(report, ensure_ascii=False)
        for forbidden in (
            "filename", "lineno", "callers", "/tmp/", "\\", "private-source",
            "source code", "cumulative_s", "generated.bin", "DDS ",
        ):
            self.assertNotIn(forbidden, output)

    def test_complete_run_not_truncated_if_profile_filters_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            manifest, prefix = profiler.generated_case(directory, 8)
            actual = profiler._profile_once(
                "dds-prefix-relations",
                lambda: build_relations(manifest, root=directory,
                                        prefix_bytes=prefix),
                8, lambda x: x["summary"]["dds_candidates"], 8)
            self.assertEqual(actual["observed_records"], 8)
            with self.assertRaisesRegex(ValueError, "incomplete"):
                profiler._profile_once(
                    "dds-prefix-relations",
                    lambda: build_relations(manifest, root=directory,
                                            prefix_bytes=prefix),
                    9, lambda x: x["summary"]["dds_candidates"], 8)

    def test_profile_output_can_limit_top_phase_count(self):
        result = profiler.profile_synthetic(
            profile="smoke", repeats=2, top_phases=1)
        for row in result["observations"]:
            self.assertEqual(len(row["phases"]), 1)

    def test_cli_writes_only_allowlisted_metadata_to_new_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "safe-metrics.json"
            result = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage159_profile",
                 "--profile", "smoke", "--repeats", "1",
                 "--output", str(output)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(data["observations"]), 4)
            self.assertNotIn(tmp, output.read_text(encoding="utf-8"))
            self.assertIn("Generated-only profiling", result.stdout)

    def test_cli_does_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "existing.json"
            output.write_text("DO-NOT-OVERWRITE", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage159_profile",
                 "--output", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("new file", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"),
                             "DO-NOT-OVERWRITE")

    def test_cli_rejects_invalid_configuration_without_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "missing.json"
            result = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage159_profile",
                 "--repeats", "100", "--output", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn("Invalid synthetic profiling", result.stderr)


if __name__ == "__main__":
    unittest.main()
