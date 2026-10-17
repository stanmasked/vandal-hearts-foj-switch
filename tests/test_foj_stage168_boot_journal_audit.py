"""Generated-only private early-boot ledger audit regressions."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from tools.foj_stage168_boot_journal_audit import (
    MAX_BYTES, parse_journal, read_journal,
)


def line(slot, stage, event, frames):
    return (f"FOJBOOT1 slot={slot:02d} step={stage:02d} "
            f"event={event} frames={frames:010d}\n").encode("ascii")


class EarlyGpuBootJournalTests(unittest.TestCase):
    def test_first_device_failure_and_no_frame_attestation(self):
        payload = line(0, 1, 1, 0) + line(0, 1, 3, 0) + line(0, 11, 4, 0)
        result = parse_journal(payload, expected_slot=0)
        self.assertEqual(result["latest_stage"], "exit")
        self.assertTrue(result["ended_with_exit_marker"])
        self.assertEqual(result["last_reported_present_calls"], 0)
        self.assertFalse(result["hardware_gpu_presentation_verified"])

    def test_first_queue_failure_and_relaunch_with_new_slot(self):
        first = b"".join([
            line(0, 1, 1, 0), line(0, 1, 2, 0),
            line(0, 2, 1, 0), line(0, 2, 3, 0),
            line(0, 11, 4, 0),
        ])
        self.assertEqual(parse_journal(first)["records"], 5)
        recovered = b"".join([
            line(1, 1, 1, 0), line(1, 1, 2, 0),
            line(1, 2, 1, 0), line(1, 2, 2, 0),
            line(1, 4, 1, 0), line(1, 4, 2, 0),
            line(1, 10, 1, 0), line(1, 10, 2, 9),
            line(1, 11, 4, 9),
        ])
        report = parse_journal(recovered, expected_slot=1)
        self.assertTrue(report["ended_with_exit_marker"])
        self.assertEqual(report["last_reported_present_calls"], 9)
        self.assertFalse(report["hardware_gpu_presentation_verified"])

    def test_incomplete_cpu_replay_not_counted_as_success(self):
        payload = line(2, 1, 1, 0) + line(2, 1, 2, 0) + line(2, 4, 1, 0)
        report = parse_journal(payload)
        self.assertEqual(report["latest_stage"], "swapchain")
        self.assertEqual(report["latest_event"], "entered")
        self.assertFalse(report["ended_with_exit_marker"])

    def test_reject_inconsistent_order_identity_and_truncation(self):
        valid = line(0, 1, 1, 0) + line(0, 1, 2, 0)
        bad = [
            b"", b"SECRET-PS3-PATH", valid[:-2], valid + b"SECRET",
            line(0, 1, 2, 0),  # ready without enter
            line(0, 1, 1, 0) + line(1, 1, 2, 0),  # foreign session
            valid + line(0, 1, 1, 0),  # stage regression
            valid + line(0, 11, 4, 0) + line(0, 11, 4, 0),
            valid + line(0, 10, 1, 5) + line(0, 10, 2, 2),
            line(0, 0, 1, 0), line(16, 1, 1, 0),
            valid + (b"x" * MAX_BYTES),
        ]
        for index, value in enumerate(bad):
            with self.subTest(index=index), self.assertRaises(ValueError):
                parse_journal(value)

    def test_local_file_basename_symlink_and_private_safe_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            log = base / "foj-boot-03.txt"
            raw = line(3, 1, 1, 0) + line(3, 1, 3, 0)
            log.write_bytes(raw)
            report = read_journal(log)
            self.assertEqual(report["slot"], 3)
            self.assertNotIn(str(base), json.dumps(report))
            link = base / "foj-boot-04.txt"
            link.symlink_to(log)
            with self.assertRaises(ValueError):
                read_journal(link)
            nonstandard = base / "a-private-source.txt"
            nonstandard.write_bytes(raw)
            with self.assertRaises(ValueError):
                read_journal(nonstandard)
            log.write_bytes(line(2, 1, 1, 0))
            with self.assertRaises(ValueError):
                read_journal(log)

    def test_cli_both_success_and_generic_malformed_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "foj-boot-00.txt"
            log.write_bytes(line(0, 1, 1, 0))
            cmd = [sys.executable, "-m", "tools.foj_stage168_boot_journal_audit",
                   "--file", str(log)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["hardware_gpu_presentation_verified"])
            self.assertNotIn(str(tmp), result.stdout)
            log.write_bytes(b"FAKE-OR-PRIVATE-SOURCE")
            rejected = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertNotIn(str(tmp), rejected.stderr)
            self.assertNotIn("FAKE-OR-PRIVATE-SOURCE", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
