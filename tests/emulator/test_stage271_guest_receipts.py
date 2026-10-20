"""Host-only schema tests; synthetic receipts here are NOT emulator proof."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.foj_stage271_evidence_check import RECEIPT,verify
from tools.foj_stage271_generated_negative_sd import CASES


def fill(root:Path):
    for case in CASES:
        folder=root/case
        folder.mkdir()
        (folder/"native-reject.txt").write_bytes(RECEIPT)
        (folder/"generated-input.json").write_text(json.dumps({
            "schema":"foj.stage271.negative_generated_actor.v1",
            "negative_case":case,
            "generated_only":True,
            "expected_native_exit_code":8,
            "guest_execution_verified":False,
        }),encoding="utf-8")
        (folder/"guest.log").write_text("synthetic fixture, NOT NeXium\n")


class ReceiptTests(unittest.TestCase):
    def test_synthetic_fixture_only_tests_classifier(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fill(root)
            r=verify(root)
            self.assertEqual(r["native_receipts_checked"],3)
            self.assertFalse(r["physical_switch_verified"])
            self.assertTrue(r["host_unit_fixtures_are_not_emulator_proof"])
            self.assertFalse(r["actual_host_process_exit_code_measured"])

    def test_missing_marker_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fill(root)
            (root/"crossing"/"native-reject.txt").unlink()
            with self.assertRaises(ValueError):verify(root)

    def test_near_match_marker_with_wrong_result_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fill(root)
            (root/"reversed"/"native-reject.txt").write_bytes(
                RECEIPT.replace(b"exit=8",b"exit=0"))
            with self.assertRaises(ValueError):verify(root)

    def test_case_swap_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fill(root)
            file=root/"coplanar"/"generated-input.json"
            data=json.loads(file.read_text())
            data["negative_case"]="reversed"
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):verify(root)

    def test_non_generated_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fill(root)
            file=root/"crossing"/"generated-input.json"
            data=json.loads(file.read_text())
            data["generated_only"]=False
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):verify(root)


if __name__=="__main__":
    unittest.main()
