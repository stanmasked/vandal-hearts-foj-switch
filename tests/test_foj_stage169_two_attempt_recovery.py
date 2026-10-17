"""Stage 169: synthetic-only C producer and strict Python recovery parity."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stage169_two_attempt_recovery import (
    _events, compare_attempts, read_strict,
)
from tools.foj_stage168_boot_journal_audit import parse_journal

ROOT = Path(__file__).resolve().parents[1]


def line(slot: int, stage: int, event: int, frames: int = 0) -> bytes:
    return (f"FOJBOOT1 slot={slot:02d} step={stage:02d} "
            f"event={event} frames={frames:010d}\n").encode("ascii")


def pack(slot: int, entries: list[tuple[int, int, int]]) -> bytes:
    return b"".join(line(slot, stage, event, frames)
                    for stage, event, frames in entries)


def starter(slot: int, failure: int | None = None,
            *, completed: bool = True) -> bytes:
    records = [(1, 1, 0), (1, 2, 0)]
    for stage in range(2, 11):
        records.append((stage, 1, 0))
        if failure == stage:
            records.append((stage, 3, 0))
            break
        records.append((stage, 2, 5 if stage == 10 else 0))
    if completed:
        records.append((11, 4, 0 if failure else 5))
    return pack(slot, records)


def parse_tuple(data: bytes, slot: int):
    base = parse_journal(data, expected_slot=slot)
    return base, _events(data)


class Stage169CpuRecoveryTests(unittest.TestCase):
    def test_real_native_c_writer_two_attempts_cross_language(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binpath = root / "c-native-fixture"
            compile_result = subprocess.run(
                ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                 "-pedantic", "-Igpu", "tests/foj_stage169_native_boot_fixture.c",
                 "gpu/gpu_boot_journal.c", "-o", str(binpath)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            created = subprocess.run([str(binpath), str(root)],
                                     capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertNotIn(str(root), created.stdout)
            older = read_strict(root / "foj-boot-00.txt")
            newer = read_strict(root / "foj-boot-01.txt")
            result = compare_attempts(older, newer)
            self.assertEqual(result["comparison"],
                             "later_attempt_reached_clean_cpu_exit")
            self.assertEqual(result["first_reported_failure_stages"], ["queue"])
            self.assertEqual(result["followup_reported_failure_stages"], [])
            self.assertEqual(result["followup_cpu_present_calls"], 5)
            self.assertEqual(result["followup_maximum_entered_stage"], "presentation")
            self.assertTrue(result["followup_exit_marker"])
            self.assertFalse(result["hardware_gpu_presentation_verified"])
            self.assertNotIn(str(root), json.dumps(result))
            self.assertNotIn("foj-boot-", json.dumps(result))

    def test_declared_recovery_never_implies_hardware_or_gameplay(self):
        r = compare_attempts(parse_tuple(starter(0, failure=2), 0),
                             parse_tuple(starter(1), 1))
        for key in ("hardware_gpu_presentation_verified",
                    "original_foj_assets_verified", "switch_gameplay_verified"):
            self.assertFalse(r[key])
        self.assertEqual(r["evidence_level"],
                         "two operator-supplied CPU checkpoint logs only")

    def test_failed_followup_is_not_a_recovery(self):
        result = compare_attempts(parse_tuple(starter(0, failure=2), 0),
                                  parse_tuple(starter(1, failure=7), 1))
        self.assertEqual(result["comparison"], "followup_failure_recorded")
        self.assertEqual(result["followup_reported_failure_stages"], ["shaders"])

    def test_incomplete_followup_is_inconclusive(self):
        after = starter(1, completed=False)
        result = compare_attempts(parse_tuple(starter(0, failure=2), 0),
                                  parse_tuple(after, 1))
        self.assertEqual(result["comparison"], "followup_log_incomplete")
        self.assertFalse(result["followup_exit_marker"])

    def test_no_first_failure_recorded_cannot_claim_recovery(self):
        result = compare_attempts(parse_tuple(starter(0), 0),
                                  parse_tuple(starter(1), 1))
        self.assertEqual(result["comparison"], "no_first_attempt_failure_recorded")

    def test_slot_order_and_nonconsecutive_slot_gap(self):
        earlier = parse_tuple(starter(1, failure=4), 1)
        later = parse_tuple(starter(4), 4)
        result = compare_attempts(earlier, later)
        self.assertEqual(result["intervening_slot_count"], 2)
        with self.assertRaisesRegex(ValueError, "distinct chronological"):
            compare_attempts(later, earlier)
        with self.assertRaisesRegex(ValueError, "distinct chronological"):
            compare_attempts(earlier, earlier)

    def test_strict_protocol_rejects_duplicate_outcomes_and_missing_enter(self):
        invalid_logs = [
            pack(0, [(1, 1, 0), (1, 2, 0), (1, 2, 0)]),
            pack(0, [(1, 1, 0), (2, 1, 0)]),
            pack(0, [(1, 1, 0), (1, 3, 0), (1, 2, 0)]),
            pack(0, [(1, 1, 0), (11, 4, 0)]),
            pack(0, [(2, 1, 0), (2, 3, 0)]),
            pack(0, [(1, 1, 4)]),
            pack(0, [(1, 1, 0), (1, 2, 0), (2, 1, 0),
                     (2, 2, 0), (2, 3, 0)]),
        ]
        for idx, blob in enumerate(invalid_logs):
            with self.subTest(case=idx), self.assertRaises(ValueError):
                _events(blob)

    def test_strict_protocol_accepts_source_error_then_error_screen(self):
        # Native NRO can report a DDS intake failure at stage 8,
        # then create a diagnostic list at stage 9 and attempt stage 10.
        blob = pack(0, [
            (1, 1, 0), (1, 2, 0),
            (8, 1, 0), (8, 3, 0),
            (9, 1, 0), (9, 2, 0),
            (10, 1, 0), (10, 3, 3),
            (11, 4, 3),
        ])
        parsed = _events(blob)
        self.assertEqual([x[1] for x in parsed if x[2] == 3], [8, 10])

    def test_nofollow_and_local_fixed_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "foj-boot-00.txt"
            first.write_bytes(starter(0, failure=2))
            symlink = root / "foj-boot-01.txt"
            symlink.symlink_to(first)
            with self.assertRaises(ValueError):
                read_strict(symlink)
            wrong = root / "private-original-ps3.txt"
            wrong.write_bytes(starter(1))
            with self.assertRaises(ValueError):
                read_strict(wrong)
            first.write_bytes(starter(1))
            with self.assertRaises(ValueError):
                read_strict(first)

    def test_cli_reports_only_structural_cpu_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "foj-boot-00.txt"
            second = root / "foj-boot-01.txt"
            first.write_bytes(starter(0, failure=2))
            second.write_bytes(starter(1))
            cmd = [sys.executable, "-m", "tools.foj_stage169_two_attempt_recovery",
                   "--before", str(first), "--after", str(second)]
            out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            result = json.loads(out.stdout)
            self.assertFalse(result["hardware_gpu_presentation_verified"])
            self.assertEqual(result["comparison"],
                             "later_attempt_reached_clean_cpu_exit")
            self.assertNotIn(str(root), out.stdout)
            swapped = subprocess.run(cmd[:4]+[str(second), "--after", str(first)],
                                     cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(swapped.returncode, 0)
            self.assertNotIn(str(root), swapped.stderr)


if __name__ == "__main__":
    unittest.main()
