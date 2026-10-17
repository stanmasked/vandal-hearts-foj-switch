"""Independent invented fixture roots; never use original PS3 game bytes."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.foj_holdout_replication import compare_cohorts


def fake_report(filename="fixture.bin", *,
                tables=((8, "little", "internally-consistent-for-private-review"),),
                positions=None):
    if positions is None:
        positions = [64 + 64 * i for i in range(len(tables))]
    observations = []
    counts = {
        "internally-contradicted": 0,
        "insufficient-or-ambiguous": 0,
        "internally-consistent-for-private-review": 0,
    }
    for (stride, endian, triage), start in zip(tables, positions):
        counts[triage] += 1
        observations.append({
            "table_start_word_offset": start,
            "stride_bytes": stride,
            "entry_count": 4,
            "byte_order": endian,
            "corroborated_pointer_rows": 4,
            "internal_triage": triage,
            "reason_codes": [] if triage == "internally-consistent-for-private-review"
                             else ["no-secondary-index-pattern"] if triage ==
                             "insufficient-or-ambiguous" else
                             ["pointer-hint-not-corroborated"],
            "game_material_or_model_link_proven": False,
        })
    return {
        "schema": "foj-cross-report-consistency-v1",
        "assessment": "same-source cross-report consistency only; not independent evidence",
        "containers": [{"relative_path": filename,
                        "table_observations": observations}],
        "summary": {
            "tables_examined": len(observations),
            "internally_contradicted": counts["internally-contradicted"],
            "insufficient_or_ambiguous": counts["insufficient-or-ambiguous"],
            "internally_consistent_for_private_review":
                counts["internally-consistent-for-private-review"],
            "foj_resource_format_confirmed": False,
        },
    }


def roots(parent):
    base = parent / "training"
    held = parent / "heldout"
    base.mkdir()
    held.mkdir()
    (base / "fixture.bin").write_bytes(b"INVENTED TRAINING DATA")
    (held / "fixture.bin").write_bytes(b"INVENTED HOLDOUT DATA")
    return base, held


class HoldoutReplicationTests(unittest.TestCase):
    def test_repeated_shape_across_separate_files_and_different_positions(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = roots(Path(d))
            first = fake_report()
            second = fake_report(positions=[256])
            result = compare_cohorts(
                first, second, baseline_root=a, holdout_root=b)
            self.assertEqual(result["patterns"][0]["stride_bytes"], 8)
            self.assertEqual(result["patterns"][0]["replication_observation"],
                             "repeated-unverified-pattern")
            self.assertEqual(result["summary"]["repeated_unverified_patterns"], 1)
            self.assertFalse(result["summary"]["sample_independence_proven"])
            self.assertFalse(result["summary"]["foj_resource_format_verified"])

    def test_structural_non_replication_and_holdout_only(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = roots(Path(d))
            first = fake_report()
            second = fake_report(tables=(
                (16, "big", "internally-consistent-for-private-review"),))
            result = compare_cohorts(first, second, baseline_root=a,
                                     holdout_root=b)
            labels = {(x["stride_bytes"], x["byte_order"]):
                      x["replication_observation"] for x in result["patterns"]}
            self.assertEqual(labels[(8, "little")], "not-reproduced-in-holdout")
            self.assertEqual(labels[(16, "big")],
                             "holdout-only-unverified-pattern")

    def test_holdout_contradiction_and_ambiguous_are_not_reproductions(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = roots(Path(d))
            first = fake_report()
            for source, expected in [
                ("internally-contradicted", "holdout-contradiction-observed"),
                ("insufficient-or-ambiguous", "holdout-ambiguous"),
            ]:
                second = fake_report(tables=((8, "little", source),))
                out = compare_cohorts(first, second, baseline_root=a,
                                      holdout_root=b)
                self.assertEqual(out["patterns"][0]["replication_observation"],
                                 expected)
                self.assertEqual(out["summary"]["repeated_unverified_patterns"], 0)

    def test_minimum_repeated_tables_and_ambiguous_only(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = roots(Path(d))
            first = fake_report(tables=(
                (8, "little", "internally-consistent-for-private-review"),
                (8, "little", "internally-consistent-for-private-review"),
            ))
            held = fake_report(tables=(
                (8, "little", "internally-consistent-for-private-review"),))
            result = compare_cohorts(first, held, baseline_root=a,
                                     holdout_root=b, min_consistent_per_cohort=2)
            self.assertEqual(result["summary"]["repeated_unverified_patterns"], 0)
            self.assertEqual(result["patterns"][0]["replication_observation"],
                             "insufficient-consistent-occurrences")
            second = fake_report(tables=(
                (8, "little", "insufficient-or-ambiguous"),))
            result = compare_cohorts(second, second, baseline_root=a,
                                     holdout_root=b)
            self.assertEqual(result["patterns"][0]["replication_observation"],
                             "insufficient-consistent-occurrences")

    def test_reject_same_root_nested_root_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            base, held = roots(Path(d))
            x = fake_report()
            with self.assertRaises(ValueError):
                compare_cohorts(x, x, baseline_root=base, holdout_root=base)
            inside = base / "nested"
            inside.mkdir()
            (inside / "fixture.bin").write_bytes(b"OTHER")
            with self.assertRaises(ValueError):
                compare_cohorts(x, x, baseline_root=base, holdout_root=inside)
            alias = Path(d) / "alias"
            alias.symlink_to(base, target_is_directory=True)
            with self.assertRaises(ValueError):
                compare_cohorts(x, x, baseline_root=alias, holdout_root=held)
            (held / "fixture.bin").unlink()
            (held / "fixture.bin").symlink_to(base / "fixture.bin")
            with self.assertRaises(ValueError):
                compare_cohorts(x, x, baseline_root=base, holdout_root=held)

    def test_hardlink_same_inode_is_not_independent(self):
        if not hasattr(os, "link"):
            self.skipTest("Hardlink not supported")
        with tempfile.TemporaryDirectory() as d:
            a, b = roots(Path(d))
            (b / "fixture.bin").unlink()
            try:
                os.link(a / "fixture.bin", b / "fixture.bin")
            except OSError:
                self.skipTest("This filesystem does not permit hardlinks")
            with self.assertRaises(ValueError):
                compare_cohorts(fake_report(), fake_report(),
                                baseline_root=a, holdout_root=b)

    def test_reject_false_and_inconsistent_report_claims(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = roots(Path(d))
            report = fake_report()
            variations = []
            t = copy.deepcopy(report);t["schema"] = "wrong";variations.append(t)
            t = copy.deepcopy(report);t["assessment"] = "verified-game";variations.append(t)
            t = copy.deepcopy(report);t["summary"]["foj_resource_format_confirmed"] = True;variations.append(t)
            t = copy.deepcopy(report);t["summary"]["tables_examined"] = 100;variations.append(t)
            t = copy.deepcopy(report);t["containers"][0]["relative_path"] = "../secret";variations.append(t)
            t = copy.deepcopy(report);t["containers"][0]["table_observations"][0]["game_material_or_model_link_proven"] = True;variations.append(t)
            t = copy.deepcopy(report);t["containers"][0]["table_observations"][0]["corroborated_pointer_rows"] = 3;variations.append(t)
            t = copy.deepcopy(report);t["containers"][0]["table_observations"][0]["reason_codes"] = ["negative"];variations.append(t)
            t = copy.deepcopy(report);t["containers"][0]["table_observations"][0]["entry_count"] = True;variations.append(t)
            t = copy.deepcopy(report);t["containers"][0]["table_observations"][0]["stride_bytes"] = 5;variations.append(t)
            for invalid in variations:
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    compare_cohorts(invalid, report, baseline_root=a,
                                    holdout_root=b)

    def test_empty_cohorts_and_input_limits(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = roots(Path(d))
            x = fake_report()
            x["containers"] = []
            x["summary"]["tables_examined"] = 0
            x["summary"]["internally_consistent_for_private_review"] = 0
            output = compare_cohorts(x, x, baseline_root=a, holdout_root=b)
            self.assertEqual(output["summary"]["patterns_compared"], 0)
            with self.assertRaises(ValueError):
                compare_cohorts(x, x, baseline_root=a, holdout_root=b,
                                min_consistent_per_cohort=0)
            with self.assertRaises(ValueError):
                compare_cohorts(x, x, baseline_root=a, holdout_root=b,
                                min_consistent_per_cohort=33)

    def test_end_to_end_two_different_synthetic_asset_sets(self):
        # The existing stage-145 fixture exercises *every* earlier analyzer;
        # the two fixture contents differ in their adjacent index ordering.
        from test_foj_evidence_triage import fixture
        from tools.foj_evidence_triage import triage_reports
        with tempfile.TemporaryDirectory() as d:
            baseline_root, holdout_root = roots(Path(d))
            baseline = triage_reports(*fixture(
                baseline_root, indices=(0, 1, 2, 3)))
            heldout = triage_reports(*fixture(
                holdout_root, indices=(2, 0, 3, 1)))
            result = compare_cohorts(
                baseline, heldout, baseline_root=baseline_root,
                holdout_root=holdout_root)
            self.assertEqual(result["baseline"]["source_files"], 1)
            self.assertEqual(result["holdout"]["source_files"], 1)
            self.assertEqual(result["summary"]["repeated_unverified_patterns"], 1)
            self.assertEqual(result["patterns"][0]["replication_observation"],
                             "repeated-unverified-pattern")
            self.assertFalse(result["summary"]["sample_independence_proven"])

    def test_cli_outputs_only_aggregate_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            a, b = roots(parent)
            first = parent / "baseline.json"
            second = parent / "holdout.json"
            output = parent / "holdout-summary.json"
            first.write_text(json.dumps(fake_report()), encoding="utf-8")
            second.write_text(json.dumps(fake_report()), encoding="utf-8")
            result = subprocess.run([
                sys.executable, "-m", "tools.foj_holdout_replication",
                "--baseline", str(first), "--holdout", str(second),
                "--baseline-root", str(a), "--holdout-root", str(b),
                "--output", str(output)
            ], capture_output=True, text=True, check=True)
            self.assertIn("Compared 1 structural patterns", result.stdout)
            data = output.read_text(encoding="utf-8")
            self.assertNotIn(str(parent), data)
            self.assertNotIn("fixture.bin", data)
            self.assertNotIn("INVENTED TRAINING DATA", data)
            self.assertFalse(json.loads(data)["summary"][
                "foj_resource_format_verified"])


if __name__ == "__main__":
    unittest.main()
