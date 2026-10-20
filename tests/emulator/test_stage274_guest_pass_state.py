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
