"""Stage-156 metadata transit limits; all fixtures contain invented data."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import sys

from tools.foj_report_transit_budget import (
    MAX_REPORT_BYTES, measure_report, read_report,
)
from tools.foj_stability_matrix import synthetic_sample
from tools.foj_source_coherence_gate import examine, publish
from tools.foj_texture_probe import inventory
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import infer_tables
from tools.foj_index_column_controls import analyze_index_columns
from tools.foj_evidence_triage import triage_reports
from tools.foj_report_replay_audit import audit_replay
import tools.foj_texture_relations as stage142
import tools.foj_resource_table_hypotheses as stage143
import tools.foj_index_column_controls as stage144
import tools.foj_evidence_triage as stage145
import tools.foj_report_replay_audit as stage149


SPEC = (4, 8, "little", "ascending", False)


class MetadataTransitBudgetTests(unittest.TestCase):
    def source(self, tmp):
        root = Path(tmp) / "invented-source"
        synthetic_sample(root, SPEC)
        return root

    def chain(self, root):
        scan = inventory(root)
        relations = build_relations(scan, root=root)
        tables = infer_tables(relations)
        indices = analyze_index_columns(tables, root=root)
        triage = triage_reports(relations, tables, indices)
        replay = audit_replay(relations, tables, indices, triage)
        return scan, relations, tables, indices, triage, replay

    def test_serialized_bytes_match_canonical_pretty_json_with_unicode(self):
        manifest = {
            "schema": "invented-stage",
            "nested": [{"имя": "файл-😀", "offset": 128}, {}, 1],
            "padding": "x" * 1024,
        }
        canonical = (json.dumps(manifest, indent=2, sort_keys=True,
                                ensure_ascii=False) + "\n").encode("utf-8")
        self.assertEqual(measure_report(manifest), len(canonical))
        self.assertEqual(measure_report(manifest, limit=len(canonical)),
                         len(canonical))
        with self.assertRaisesRegex(ValueError, "byte budget"):
            measure_report(manifest, limit=len(canonical)-1)

    def test_too_large_single_metadata_string_rejected_without_leak(self):
        secret = "private-source-witness-DO-NOT-PUBLISH"
        value = {"secret": secret + "z" * 2400}
        with self.assertRaises(ValueError) as caught:
            measure_report(value, limit=1024)
        self.assertNotIn(secret, str(caught.exception))

    def test_non_json_object_and_invalid_budget_rejected(self):
        for obj in ([], None, "abc"):
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                measure_report(obj)
        for limit in (-1, 0, 1023, True, MAX_REPORT_BYTES+1):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                measure_report({"a": "b"}, limit=limit)

    def test_nonfinite_float_cannot_pass_report_transfer(self):
        with self.assertRaises(ValueError):
            measure_report({"x": float("nan")})

    def test_regular_local_json_read_roundtrip_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "report.json"
            report = {"schema": "invented", "records": [{"n": 4}]}
            file.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual(read_report(file), report)
            file.write_text('{"key":1,"key":2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
                read_report(file)
            file.write_text('{"x": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Non-finite"):
                read_report(file)

    def test_symlink_missing_and_directory_never_opened_as_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "metadata.json"
            original.write_text('{"schema": "invented"}', encoding="utf-8")
            (root / "link.json").symlink_to(original)
            for path in (root / "link.json", root / "missing.json", root):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    read_report(path)

    def test_sparse_oversized_report_rejected_before_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "large.json"
            with file.open("wb") as stream:
                stream.truncate(MAX_REPORT_BYTES+1)
            self.assertEqual(file.stat().st_size, MAX_REPORT_BYTES+1)
            with self.assertRaisesRegex(ValueError, "input byte budget"):
                read_report(file)

    def test_corrupted_utf8_is_not_misreported_as_source_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "bad.json"
            file.write_bytes(b'{"x":"\xff"}')
            with self.assertRaisesRegex(ValueError, "Invalid local report JSON"):
                read_report(file)

    def test_pipeline_all_six_reports_stay_in_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.source(tmp)
            reports = self.chain(root)
            self.assertEqual(len(reports), 6)
            for report in reports:
                self.assertLessEqual(measure_report(report), MAX_REPORT_BYTES)
            self.assertTrue(reports[-1]["summary"]["tables_replayed"] >= 0)
            self.assertTrue(reports[-1]["summary"]["original_foj_asset_proven"] is False)

    def test_each_stage_checks_input_and_result_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.source(tmp)
            scan, relations, tables, indices, triage, _ = self.chain(root)
            calls = [
                (stage142, lambda: build_relations(scan, root=root), 2),
                (stage143, lambda: infer_tables(relations), 2),
                (stage144, lambda: analyze_index_columns(tables, root=root), 2),
                (stage145, lambda: triage_reports(relations, tables, indices), 4),
                (stage149, lambda: audit_replay(relations, tables, indices, triage), 5),
            ]
            for module, operation, expected in calls:
                real_measure = module.measure_report
                seen = []
                def wrapped(*args, **kwargs):
                    seen.append(True)
                    return real_measure(*args, **kwargs)
                with patch.object(module, "measure_report", side_effect=wrapped):
                    operation()
                self.assertEqual(len(seen), expected, module.__name__)

    def test_input_overflow_stops_stage_before_opening_pointer_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.source(tmp)
            scan = inventory(root)
            real = stage142.measure_report
            with patch.object(stage142, "measure_report",
                              side_effect=lambda report: real(report, limit=1024)):
                with patch.object(stage142, "_read_prefix") as read_bytes:
                    with self.assertRaisesRegex(ValueError, "byte budget"):
                        stage142.build_relations(scan, root=root)
                    read_bytes.assert_not_called()

    def test_coherent_report_bundle_budget_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.source(tmp)
            output = Path(tmp) / "not-published"
            with self.assertRaisesRegex(ValueError, "bundle byte budget"):
                publish(root, output, max_bundle_bytes=1024)
            self.assertFalse(output.exists())
            self.assertFalse(list(Path(tmp).glob(".foj-stage150-*")))
            finished = examine(root, max_bundle_bytes=128 * 1024 * 1024)
            self.assertEqual(finished[-1]["status"], "two-snapshots-match")

    def test_standalone_stage142_refuses_oversized_input_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "untrusted.json"
            output = Path(tmp) / "should-not-exist.json"
            with report.open("wb") as stream:
                stream.truncate(MAX_REPORT_BYTES + 1)
            proc = subprocess.run(
                [sys.executable, "-m", "tools.foj_texture_relations",
                 str(report), "--output", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn("byte budget", proc.stderr)
            self.assertNotIn(str(report), proc.stderr)

    def test_oversized_input_guard_all_standalone_consumers(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "large.json"
            with report.open("wb") as stream:
                stream.truncate(MAX_REPORT_BYTES + 1)
            for module, arguments in (
                ("tools.foj_resource_table_hypotheses", [str(report)]),
                ("tools.foj_index_column_controls", [
                    str(report), "--root", tmp]),
                ("tools.foj_evidence_triage", [
                    "--relations", str(report), "--tables", str(report),
                    "--indices", str(report)]),
                ("tools.foj_report_replay_audit", [
                    "--relations", str(report), "--tables", str(report),
                    "--indices", str(report), "--triage", str(report)]),
            ):
                with self.subTest(module=module):
                    out = Path(tmp) / "not-created.json"
                    proc = subprocess.run(
                        [sys.executable, "-m", module, *arguments,
                         "--output", str(out)],
                        capture_output=True, text=True)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertFalse(out.exists())
                    self.assertIn("byte budget", proc.stderr)


if __name__ == "__main__":
    unittest.main()
