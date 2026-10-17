"""Stage 155 global DDS candidate budgets: invented temporary files only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.foj_stability_matrix import synthetic_sample
from tools.foj_texture_probe import (
    DEFAULT_MAX_CANDIDATES, DEFAULT_MAX_METADATA_BYTES,
    HARD_MAX_CANDIDATES, HARD_MAX_METADATA_BYTES,
    inventory,
)
from tools.foj_source_coherence_gate import examine, publish
import tools.foj_texture_probe as probe

SPEC = (4, 8, "little", "ascending", False)


class GlobalCandidateBudgetTests(unittest.TestCase):
    def _source(self, base):
        root = Path(base) / "private"
        synthetic_sample(root, SPEC)
        return root

    def test_global_record_budget_rejects_fourth_real_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            with self.assertRaisesRegex(ValueError, "Total DDS candidate limit"):
                inventory(root, max_candidates=3)
            complete = inventory(root, max_candidates=4)
            self.assertEqual(len(complete["candidates"]), 4)
            self.assertEqual(complete["schema"], "foj-texture-candidates-v1")
            self.assertEqual(complete["scan_truncated_at_file_limit"], False)

    def test_global_budget_across_multiple_files_not_per_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            bytes_ = (root / "synthetic.bin").read_bytes()
            (root / "synthetic2.bin").write_bytes(bytes_)
            with self.assertRaisesRegex(ValueError, "Total DDS candidate limit"):
                inventory(root, max_candidates=7)
            self.assertEqual(len(inventory(root, max_candidates=8)["candidates"]), 8)

    def test_metadata_byte_budget_prevents_record_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            with self.assertRaisesRegex(ValueError, "metadata byte budget"):
                inventory(root, max_metadata_bytes=1024)
            complete = inventory(root, max_metadata_bytes=8192)
            encoded = (json.dumps(complete, ensure_ascii=False, sort_keys=True,
                                  indent=2) + "\n").encode("utf-8")
            self.assertLessEqual(len(encoded), 8192)

    def test_utf8_and_path_length_count_against_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            (root / "synthetic.bin").rename(
                root / ("Файл-исследования-" + "я" * 50 + ".bin"))
            with self.assertRaisesRegex(ValueError, "metadata byte budget"):
                inventory(root, max_metadata_bytes=1024)
            stable = inventory(root)
            self.assertEqual(len(stable["candidates"]), 4)
            self.assertNotIn(str(root), json.dumps(stable, ensure_ascii=False))

    def test_many_well_formed_generated_dds_records_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            content = (root / "synthetic.bin").read_bytes()
            for i in range(40):
                (root / f"copy-{i:03}.bin").write_bytes(content)
            with self.assertRaisesRegex(ValueError, "candidate limit"):
                inventory(root, max_candidates=128, max_files=100)
            self.assertEqual(len(inventory(root, max_candidates=164,
                                           max_files=100)["candidates"]), 164)

    def test_zero_candidate_scan_still_respects_output_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "noise.bin").write_bytes(b"\xff" * 4096)
            outcome = inventory(root, max_candidates=1,
                                max_metadata_bytes=1024)
            self.assertEqual(outcome["candidates"], [])
            self.assertEqual(outcome["files_scanned"], 1)

    def test_invalid_bounds_rejected_before_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            for kwargs in (
                {"max_candidates": 0},
                {"max_candidates": True},
                {"max_candidates": -1},
                {"max_candidates": HARD_MAX_CANDIDATES + 1},
                {"max_metadata_bytes": 1023},
                {"max_metadata_bytes": True},
                {"max_metadata_bytes": HARD_MAX_METADATA_BYTES + 1},
            ):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaisesRegex(ValueError, "limits"):
                        inventory(root, **kwargs)

    def test_coherence_gate_applies_candidate_limit_and_no_partial_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            output = Path(tmp) / "unpublished"
            with self.assertRaisesRegex(ValueError, "candidate limit"):
                publish(root, output, max_candidates=3)
            self.assertFalse(output.exists())
            self.assertFalse(list(Path(tmp).glob(".foj-stage150-*")))

    def test_coherence_gate_applies_byte_limit_and_no_partial_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            output = Path(tmp) / "unpublished"
            with self.assertRaisesRegex(ValueError, "metadata byte budget"):
                publish(root, output, max_metadata_bytes=1024)
            self.assertFalse(output.exists())
            finished = examine(root, max_candidates=4,
                               max_metadata_bytes=8192)
            self.assertEqual(finished[-1]["summary"]["dds_candidates"], 4)
            self.assertTrue(finished[-1]["summary"]["replay_verified"])

    def test_cli_rejects_too_many_candidates_before_writing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            report = Path(tmp) / "no-report.json"
            proc = subprocess.run(
                [sys.executable, "-m", "tools.foj_texture_probe",
                 str(root), "--output", str(report), "--max-candidates", "3"],
                text=True, capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(report.exists())
            self.assertIn("candidate limit", proc.stderr)
            self.assertNotIn(str(root), proc.stderr)

    def test_cli_coherence_candidate_limit_has_no_partial_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            out = Path(tmp) / "no-publish"
            proc = subprocess.run(
                [sys.executable, "-m", "tools.foj_source_coherence_gate",
                 str(root), "--output-dir", str(out), "--max-candidates", "3"],
                text=True, capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(out.exists())
            self.assertIn("candidate limit", proc.stderr)
            self.assertNotIn(str(root), proc.stderr)

    def test_default_budget_is_explicit_and_report_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._source(tmp)
            self.assertEqual(DEFAULT_MAX_CANDIDATES, 8192)
            self.assertEqual(DEFAULT_MAX_METADATA_BYTES, 8 * 1024 * 1024)
            with patch.object(probe, "_verified_header_candidates",
                              wraps=probe._verified_header_candidates) as verified:
                output = inventory(root)
            self.assertTrue(verified.called)
            self.assertEqual(len(output["candidates"]), 4)
            self.assertNotIn("max_candidates", output)
            self.assertNotIn("max_metadata_bytes", output)


if __name__ == "__main__":
    unittest.main()
