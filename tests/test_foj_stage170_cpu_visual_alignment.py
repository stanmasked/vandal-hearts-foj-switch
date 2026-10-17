"""Generated-only stage-170 CPU/visual linkage regression tests.

All supplied "screen outcomes" are invented fixtures, never photographs
or real observations from Nintendo Switch hardware.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stage166_hardware_observations import (
    SCENARIOS, audit, blank_template, read_ledger,
)
from tools.foj_stage170_cpu_visual_alignment import (
    LINK_BASIS, align, blank_link, create_blank_link, read_link,
    validate_link,
)
from tools.foj_stage169_two_attempt_recovery import read_strict

ROOT = Path(__file__).resolve().parents[1]


def line(slot, stage, event, frames=0):
    return (f"FOJBOOT1 slot={slot:02d} step={stage:02d} "
            f"event={event} frames={frames:010d}\n").encode()


def failed(slot):
    return b"".join([
        line(slot, 1, 1), line(slot, 1, 2), line(slot, 2, 1),
        line(slot, 2, 3), line(slot, 11, 4),
    ])


def passing(slot):
    rows = []
    for stage in range(1, 11):
        rows.append(line(slot, stage, 1))
        rows.append(line(slot, stage, 2, 5 if stage == 10 else 0))
    rows.append(line(slot, 11, 4, 5))
    return b"".join(rows)


def visual_sheet(scenario="C", *, count=3):
    sheet = blank_template()
    if scenario is not None:
        entry = sheet["scenarios"][list(SCENARIOS).index(scenario)]
        for visual, expected in zip(entry["observations"][:count],
                                    SCENARIOS[scenario]):
            visual["seen"] = expected
    return sheet


def linked(slot, scenario):
    return {
        "schema": blank_link()["schema"],
        "boot_slot": slot,
        "visual_scenario": scenario,
        "association_basis": LINK_BASIS,
    }


class Stage170AlignmentTests(unittest.TestCase):
    def with_inputs(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        before = root / "foj-boot-00.txt"
        after = root / "foj-boot-01.txt"
        before.write_bytes(failed(0))
        after.write_bytes(passing(1))
        return temp, root, before, after

    def test_blank_link_never_claims_visual_alignment(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            result = align(read_strict(before), read_strict(after),
                           visual_sheet(), blank_link())
            self.assertEqual(result["cpu_recovery_comparison"],
                             "later_attempt_reached_clean_cpu_exit")
            self.assertEqual(result["cpu_visual_alignment"], "not_linked")
            self.assertFalse(result["operator_link_explicit"])
            self.assertIsNone(result["linked_slot"])
            self.assertFalse(result["hardware_execution_verified"])
            self.assertFalse(result["gpu_scanout_verified"])
            self.assertFalse(result["original_foj_assets_verified"])

    def test_synthetic_matching_colors_are_only_consistent_declarations(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            result = align(read_strict(before), read_strict(after),
                           visual_sheet("C"), linked(1, "C"))
            self.assertEqual(result["linked_scenario"], "C")
            self.assertEqual(result["linked_observed_stages"], 3)
            self.assertEqual(result["operator_visual_expected_comparison"],
                             "matches_synthetic_expectations")
            self.assertEqual(result["cpu_visual_alignment"],
                             "cpu_and_operator_declarations_consistent_unverified")
            self.assertTrue(result["operator_link_explicit"])
            self.assertFalse(result["hardware_execution_verified"])
            self.assertFalse(result["gpu_scanout_verified"])
            self.assertNotIn(str(root), json.dumps(result))

    def test_earlier_cpu_failure_linked_to_visual_claim_requires_recheck(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            result = align(read_strict(before), read_strict(after),
                           visual_sheet("C"), linked(0, "C"))
            self.assertEqual(result["cpu_visual_alignment"],
                             "cpu_journal_does_not_support_visual_sequence")
            self.assertFalse(result["hardware_execution_verified"])

    def test_operator_color_mismatch_is_not_silently_corrected(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            sheet = visual_sheet("C")
            sheet["scenarios"][2]["observations"][0]["seen"] = "blue"
            self.assertEqual(audit(sheet)["scenarios"][2]["comparison"],
                             "differs_from_expected")
            result = align(read_strict(before), read_strict(after),
                           sheet, linked(1, "C"))
            self.assertEqual(result["cpu_visual_alignment"],
                             "operator_visual_differs_from_test_expectations")
            self.assertFalse(result["gpu_scanout_verified"])

    def test_partially_filled_visual_statement_remains_incomplete(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            result = align(read_strict(before), read_strict(after),
                           visual_sheet("C", count=2), linked(1, "C"))
            self.assertEqual(result["linked_observed_stages"], 2)
            self.assertEqual(result["cpu_visual_alignment"],
                             "incomplete_operator_visual_observation")

    def test_explicit_link_with_zero_visual_observations(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            result = align(read_strict(before), read_strict(after),
                           visual_sheet(), linked(1, "D"))
            self.assertEqual(result["cpu_visual_alignment"],
                             "no_operator_visual_observation")
            self.assertEqual(result["operator_visual_expected_comparison"],
                             "not_observed")

    def test_foreign_slot_and_malformed_link_fail_closed(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            a, b = read_strict(before), read_strict(after)
            with self.assertRaises(ValueError):
                align(a, b, visual_sheet("C"), linked(2, "C"))
            examples = [
                {"schema": blank_link()["schema"], "boot_slot": 1},
                linked(True, "C"), linked(17, "C"),
                linked(1, "ZZ"), linked(1, "C") | {"unexpected": 5},
                linked(1, "C") | {"association_basis": "automatic"},
                linked(1, "C") | {"boot_slot": None},
                blank_link() | {"visual_scenario": "C"},
            ]
            for idx, case in enumerate(examples):
                with self.subTest(index=idx), self.assertRaises(ValueError):
                    validate_link(case)

    def test_blank_link_is_written_exclusively_and_kept_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "association.json"
            create_blank_link(target)
            self.assertEqual(read_link(target), blank_link())
            saved = target.read_bytes()
            with self.assertRaisesRegex(ValueError, "new file"):
                create_blank_link(target)
            self.assertEqual(saved, target.read_bytes())
            target.write_text('{"schema":1,"schema":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_link(target)

    def test_link_symlink_and_bad_local_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            link = root / "linked.json"
            original = root / "private.json"
            original.write_text(json.dumps(linked(1, "C")), encoding="utf-8")
            link.symlink_to(original)
            with self.assertRaises(ValueError):
                read_link(link)
            original.write_bytes(b"{" + b"A" * 4096 + b"}")
            with self.assertRaises(ValueError):
                read_link(original)

    def test_cli_blank_template_and_unlinked_audit(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            link = root / "binding.json"
            sheet = root / "observations.json"
            init = subprocess.run(
                [sys.executable, "-m", "tools.foj_stage170_cpu_visual_alignment",
                 "--init-link", str(link)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertIn("BLANK", init.stdout)
            sheet.write_text(json.dumps(visual_sheet()), encoding="utf-8")
            cmd = [sys.executable, "-m", "tools.foj_stage170_cpu_visual_alignment",
                   "--before", str(before), "--after", str(after),
                   "--ledger", str(sheet), "--link", str(link)]
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)["cpu_visual_alignment"],
                             "not_linked")
            self.assertNotIn(str(root), run.stdout)
            self.assertFalse(json.loads(run.stdout)["hardware_execution_verified"])

    def test_cli_operator_explicit_link_and_error_privacy(self):
        temp, root, before, after = self.with_inputs()
        with temp:
            link = root / "link.json"
            sheet = root / "views.json"
            link.write_text(json.dumps(linked(1, "C")), encoding="utf-8")
            sheet.write_text(json.dumps(visual_sheet("C")), encoding="utf-8")
            cmd = [sys.executable, "-m", "tools.foj_stage170_cpu_visual_alignment",
                   "--before", str(before), "--after", str(after),
                   "--ledger", str(sheet), "--link", str(link)]
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(json.loads(run.stdout)["operator_link_explicit"])
            self.assertNotIn(str(root), run.stdout)
            link.write_text('{"private":"/home/example/game-data"}', encoding="utf-8")
            bad = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertNotIn(str(root), bad.stderr)
            self.assertNotIn("game-data", bad.stderr)

    def test_real_C_record_writer_cross_checked_with_operator_fixture(self):
        # Cross-check the actual native stage-168 C journal producer.
        temp, root, before, after = self.with_inputs()
        with temp:
            executable = root / "producer"
            cc = subprocess.run(
                ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-Igpu", "tests/foj_stage169_native_boot_fixture.c",
                 "gpu/gpu_boot_journal.c", "-o", str(executable)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(cc.returncode, 0, cc.stderr)
            before.unlink()
            after.unlink()
            produced = subprocess.run([str(executable), str(root)],
                                      cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(produced.returncode, 0, produced.stderr)
            result = align(read_strict(before), read_strict(after),
                           visual_sheet("C"), linked(1, "C"))
            self.assertEqual(result["cpu_visual_alignment"],
                             "cpu_and_operator_declarations_consistent_unverified")
            self.assertFalse(result["hardware_execution_verified"])
            self.assertEqual(result["cpu_recovery_comparison"],
                             "later_attempt_reached_clean_cpu_exit")


if __name__ == "__main__":
    unittest.main()
