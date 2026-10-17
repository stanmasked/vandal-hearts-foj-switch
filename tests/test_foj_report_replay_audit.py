"""Strict JSON replay tests use invented DDS bytes, not original PS3 data."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stability_matrix import FILE_BYTES, synthetic_sample
from tools.foj_texture_probe import inventory
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import infer_tables
from tools.foj_index_column_controls import analyze_index_columns
from tools.foj_evidence_triage import triage_reports
from tools.foj_report_replay_audit import audit_replay, _read_report
from tools.foj_corrupt_container_matrix import _mutate


SPEC = (4, 8, "little", "ascending", False)


def invented_chain(root: Path, *, truncate=False):
    synthetic_sample(root, SPEC)
    if truncate:
        path = root / "synthetic.bin"
        path.write_bytes(_mutate(path.read_bytes(), "truncated-last-image"))
    layout = build_relations(
        inventory(root), root=root, prefix_bytes=FILE_BYTES)
    tables = infer_tables(layout)
    indices = analyze_index_columns(
        tables, root=root, prefix_bytes=FILE_BYTES,
        max_control_windows=1024)
    triage = triage_reports(layout, tables, indices)
    return layout, tables, indices, triage


class ReportReplayAuditTests(unittest.TestCase):
    def test_complete_invented_chain_replays_without_proving_a_game_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = audit_replay(*invented_chain(Path(tmp) / "invented"))
        self.assertEqual(result["status"], "internally-replayed")
        self.assertEqual(result["summary"]["tables_replayed"], 1)
        self.assertEqual(
            result["summary"]["triage_internally_consistent_for_private_review"], 1)
        self.assertFalse(result["summary"]["original_foj_asset_proven"])
        self.assertFalse(result["summary"]["nintendo_switch_runtime_verified"])
        self.assertNotIn("relative_path", json.dumps(result))

    def test_truncated_dds_is_a_valid_replay_of_a_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            chain = invented_chain(Path(tmp) / "invented", truncate=True)
            replay = audit_replay(*chain)
            self.assertEqual(
                replay["summary"]["triage_internally_contradicted"], 1)
            self.assertEqual(replay["summary"]["tables_replayed"], 1)

    def test_forged_and_missing_stage_143_table_records_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            chain = invented_chain(Path(tmp) / "invented")
            altered = copy.deepcopy(chain)
            altered[1]["containers"][0]["table_hypotheses"][0][
                "target_dds_offsets"][0] += 8
            with self.assertRaisesRegex(ValueError, "does not replay"):
                audit_replay(*altered)
            altered = copy.deepcopy(chain)
            altered[1]["containers"] = []
            with self.assertRaisesRegex(ValueError, "does not replay"):
                audit_replay(*altered)

    def test_stage_143_threshold_and_supported_stride_mismatch_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            chain = invented_chain(Path(tmp) / "invented")
            altered = copy.deepcopy(chain)
            altered[1]["minimum_distinct_dds_targets"] = 17
            with self.assertRaises(ValueError):
                audit_replay(*altered)
            altered = copy.deepcopy(chain)
            altered[1]["allowed_strides_bytes"] = [8, 16]
            with self.assertRaises(ValueError):
                audit_replay(*altered)

    def test_missing_or_extra_stage_144_observations_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            chain = invented_chain(Path(tmp) / "invented")
            altered = copy.deepcopy(chain)
            altered[2]["containers"] = []
            with self.assertRaisesRegex(ValueError, "coverage"):
                audit_replay(*altered)
            altered = copy.deepcopy(chain)
            rows = altered[2]["containers"][0]["examined_tables"]
            rows.append(copy.deepcopy(rows[0]))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                audit_replay(*altered)

    def test_stage_144_label_field_and_window_tampering_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            chain = invented_chain(Path(tmp) / "invented")
            altered = copy.deepcopy(chain)
            altered[2]["containers"][0]["examined_tables"][0][
                "structural_observation"] = "no-index-like-field"
            with self.assertRaisesRegex(ValueError, "contradicts"):
                audit_replay(*altered)
            altered = copy.deepcopy(chain)
            altered[2]["containers"][0]["examined_tables"][0][
                "independent_control_dense_windows"] = 9000
            with self.assertRaises(ValueError):
                audit_replay(*altered)
            altered = copy.deepcopy(chain)
            altered[2]["containers"][0]["examined_tables"][0][
                "possible_secondary_index_fields"][0][
                    "field_delta_from_pointer_bytes"] = 3
            with self.assertRaisesRegex(ValueError, "position"):
                audit_replay(*altered)

    def test_modified_stage_145_outcome_fails_even_with_valid_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            chain = invented_chain(Path(tmp) / "invented")
            altered = copy.deepcopy(chain)
            altered[3]["summary"]["internally_contradicted"] += 1
            with self.assertRaisesRegex(ValueError, "does not replay"):
                audit_replay(*altered)

    def test_cli_reports_only_aggregate_and_rejects_changed_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chain = invented_chain(root / "invented")
            files = [root / f"metadata-{i}.json" for i in range(4)]
            for path, report in zip(files, chain):
                path.write_text(json.dumps(report), encoding="utf-8")
            out = root / "replay.json"
            cmd = [
                sys.executable, "-m", "tools.foj_report_replay_audit",
                "--relations", str(files[0]), "--tables", str(files[1]),
                "--indices", str(files[2]), "--triage", str(files[3]),
                "--output", str(out),
            ]
            success = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(success.returncode, 0, success.stderr)
            payload = out.read_text(encoding="utf-8")
            self.assertNotIn(str(root), payload)
            self.assertNotIn("synthetic.bin", payload)
            self.assertIn("tables_replayed", payload)
            chain[3]["summary"]["tables_examined"] += 1
            files[3].write_text(json.dumps(chain[3]), encoding="utf-8")
            failure = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn("does not replay", failure.stderr)

    def test_duplicate_json_members_and_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "dupe.json"
            source.write_text('{"schema":"first","schema":"second"}',
                              encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
                _read_report(source)
            source.write_text("{}", encoding="utf-8")
            link = root / "link.json"
            link.symlink_to(source)
            with self.assertRaisesRegex(ValueError, "non-symlink"):
                _read_report(link)


if __name__ == "__main__":
    unittest.main()
