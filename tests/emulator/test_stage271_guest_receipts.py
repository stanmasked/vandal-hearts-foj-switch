"""Host-only schema tests; synthetic receipts here are NOT emulator proof."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.foj_stage271_evidence_check import RECEIPT,verify
from tools.foj_stage271_generated_negative_sd import CASES
from PIL import Image, ImageDraw


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


def fill_safe_control(control: Path, wrong: bool=False):
    control.mkdir()
    (control/"guest.log").write_text("synthetic test, NOT NeXium\\n")
    (control/"generated-input.json").write_text(json.dumps({
        "schema":"foj.stage267.generated_three_layer.v1",
        "case":"both-half",
        "generated_only":True,
        "stage269_geometry_guard":"safe_fixed_back_to_front",
        "stage269_checked_order":["cool","warm","violet"]
    }))
    from tools.foj_stage267_gpu_three_layer_check import PROBES
    for filename,background in (("gpu-initial.png",(54,31,59)),
                                ("gpu-later.png",(112,145,110))):
        frame=Image.new("RGB",(1280,720),background)
        draw=ImageDraw.Draw(frame)
        for key,(x,y) in PROBES.items():
            color=((21,202,219) if key=="rear_only"
                   else ((96,72,201) if wrong else (111,100,162)))
            draw.rectangle((x-10,y-10,x+10,y+10),fill=color)
        frame.save(control/filename)


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

    def test_safe_control_synthetic_fixture_only_tests_classifier(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fill(root)
            control=root/"safe-control"
            fill_safe_control(control)
            result=verify(root,control)
            self.assertEqual(result["native_receipts_checked"],3)
            self.assertEqual(result["positive_control"]["scenario"],"both-half")
            self.assertTrue(result["positive_control"]["gpu_clear_phase_changed"])
            self.assertFalse(result["actual_host_process_exit_code_measured"])

    def test_safe_control_wrong_rgb_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fill(root)
            control=root/"safe-control"
            fill_safe_control(control,wrong=True)
            with self.assertRaises(ValueError):
                verify(root,control)

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
