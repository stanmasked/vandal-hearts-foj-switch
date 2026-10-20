"""Stage274 independent classifier tests: mock files are NEVER GPU proof."""
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage273_dynamic_gpu_sd import (
    CASES, BACK_TO_FRONT, expected_rgb,
)
from tools.foj_stage267_gpu_three_layer_check import PROBES
from tools.foj_stage274_pass_contract_check import (
    expected_receipt, verify,
)


def generate_mock_evidence(root:Path):
    for case in CASES:
        dest=root/case
        dest.mkdir(parents=True)
        (dest/"generated-input.json").write_text(json.dumps({
            "schema":"foj.stage273.dynamic_gpu_sort.v1",
            "scenario":case,
            "expected_native_pass_order":list(BACK_TO_FRONT[case]),
            "expected_overlap_rgb":list(expected_rgb(case)),
            "generated_only":True,
            "guest_proof_claimed":False,
        }),encoding="utf-8")
        draw="FOJ_NATIVE_SORT_V1 "+",".join(
            str(n) for n in BACK_TO_FRONT[case])+"\n"
        (dest/"native-sort-pass.txt").write_bytes(draw.encode("ascii"))
        (dest/"native-alpha-pass.txt").write_bytes(expected_receipt(case))
        for phase,(name,background) in enumerate((
            ("gpu-initial.png",(40,28,75)),
            ("gpu-later.png",(96,136,114)),
        )):
            image=Image.new("RGB",(1280,720),background)
            paint=ImageDraw.Draw(image)
            for label,(x,y) in PROBES.items():
                rgb=(21,202,219) if label=="rear_only" else expected_rgb(case)
                paint.rectangle((x-7,y-7,x+7,y+7),fill=rgb)
            image.save(dest/name)


    negative=root/"rear-alpha-negative"
    negative.mkdir()
    (negative/"generated-input.json").write_text(json.dumps({
        "schema":"foj.stage274.native_rear_alpha_negative.v1",
        "scenario":"one-rear-alpha-254",
        "generated_only":True,
        "original_ps3_resources":False,
        "guest_verified":False,
        "changed_file":"material2.dds",
        "changed_bytes":1,
        "original_alpha":255,
        "mutated_alpha":254,
        "expected_native_rejection_marker":
            "FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1",
    }),encoding="utf-8")
    (negative/"native-rear-alpha-reject.txt").write_bytes(
        b"FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1\n")
    (negative/"guest.log").write_text(
        "synthetic classifier fixture, NOT real guest execution\n",
        encoding="utf-8")


class Stage274PassEvidenceTests(unittest.TestCase):
    def test_generated_receipt_has_native_state_for_both_orders(self):
        self.assertEqual(expected_receipt("original"),
            b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0\n")
        self.assertEqual(expected_receipt("reversed"),
            b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 0:1:1:0 1:1:1:0\n")
        with self.assertRaises(ValueError):
            expected_receipt("unknown")

    def test_synthetic_classifier_acceptance_is_not_real_guest_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            generate_mock_evidence(folder)
            result=verify(folder)
            self.assertEqual(result["guest_native_pass_state_receipts"],2)
            self.assertEqual(result["native_rear_alpha_rejection_receipts"],1)
            self.assertTrue(result["negative_generated_rear_dds_refused_before_gpu"])
            self.assertEqual(result["stage273_independent_frame_audit"][
                "verified_guest_frames"],4)
            self.assertEqual(result["actual_guest_provenance"],
                             "requires real NeXium GitHub Actions workflow")

    def test_wrong_depth_write_rejected_even_if_all_rgb_looks_right(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            generate_mock_evidence(folder)
            (folder/"original"/"native-alpha-pass.txt").write_bytes(
                b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:1 0:1:1:0\n")
            with self.assertRaisesRegex(ValueError,"native GPU blend/depth"):
                verify(folder)

    def test_swapped_material_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            generate_mock_evidence(folder)
            (folder/"original"/"native-alpha-pass.txt").write_bytes(
                expected_receipt("reversed"))
            with self.assertRaisesRegex(ValueError,"native GPU blend/depth"):
                verify(folder)

    def test_missing_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            generate_mock_evidence(folder)
            (folder/"reversed"/"native-alpha-pass.txt").unlink()
            with self.assertRaisesRegex(ValueError,"native GPU blend/depth"):
                verify(folder)

    def test_missing_negative_guest_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            generate_mock_evidence(folder)
            (folder/"rear-alpha-negative"/"native-rear-alpha-reject.txt").unlink()
            with self.assertRaisesRegex(ValueError,"negative guest evidence"):
                verify(folder)

    def test_wrong_native_rear_alpha_marker_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            generate_mock_evidence(folder)
            (folder/"rear-alpha-negative"/"native-rear-alpha-reject.txt").write_bytes(
                b"FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=0\n")
            with self.assertRaisesRegex(ValueError,"rear DDS refusal"):
                verify(folder)

    def test_wrong_negative_generated_dds_provenance_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            generate_mock_evidence(folder)
            path=folder/"rear-alpha-negative"/"generated-input.json"
            report=json.loads(path.read_text())
            report["changed_bytes"]=2
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,"rear DDS refusal"):
                verify(folder)

    def test_correct_pass_marker_does_not_rescue_duplicate_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            generate_mock_evidence(folder)
            data=(folder/"original"/"gpu-initial.png").read_bytes()
            (folder/"original"/"gpu-later.png").write_bytes(data)
            with self.assertRaises(ValueError):
                verify(folder)


if __name__=="__main__":
    unittest.main()
