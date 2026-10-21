"""Stage275 host synthetic classifier tests; these never prove guest runs."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import ctypes as c
from PIL import Image,ImageDraw
from test_stage274_actual_native_chain import (
    compile_pipeline, Stage274ActualNativeChain, Section, Camera,
    Vertex, Batch, StreamInfo, U32,
)

from tools.foj_stage267_gpu_three_layer_check import PROBES
from tools.foj_stage271_generated_negative_sd import rejected_actor
from tools.foj_stage273_dynamic_gpu_sd import (
    generated_actor,safe_draw_order,expected_rgb,
)
from tools.foj_stage268_transparency_crossing import UnsafeTransparencyOrder
from tools.foj_stage275_negative_topology_sd import CASES,SCHEMA,MESSAGE
from tools.foj_stage275_topology_evidence_check import verify
from tools.foj_stage274_pass_contract_check import expected_receipt


def fixture(root:Path):
    positive=root/"original"
    positive.mkdir()
    (positive/"generated-input.json").write_text(json.dumps({
        "schema":"foj.stage273.dynamic_gpu_sort.v1",
        "scenario":"original",
        "generated_only":True,
        "guest_proof_claimed":False,
        "expected_native_pass_order":[2,1,0],
        "expected_overlap_rgb":list(expected_rgb("original")),
    }),encoding="utf-8")
    (positive/"native-sort-pass.txt").write_bytes(
        b"FOJ_NATIVE_SORT_V1 2,1,0\n")
    (positive/"native-alpha-pass.txt").write_bytes(
        expected_receipt("original"))
    for filename,background in (
        ("gpu-initial.png",(112,145,110)),
        ("gpu-later.png",(54,31,59)),
    ):
        image=Image.new("RGB",(1280,720),background)
        draw=ImageDraw.Draw(image)
        for name,(x,y) in PROBES.items():
            color=(21,202,219) if name=="rear_only" else expected_rgb("original")
            draw.rectangle((x-8,y-8,x+8,y+8),fill=color)
        image.save(positive/filename)
    safe=hashlib.sha256(generated_actor("original")).hexdigest()
    for case in CASES:
        folder=root/case
        folder.mkdir()
        digest=hashlib.sha256(rejected_actor(case)).hexdigest()
        (folder/"generated-input.json").write_text(json.dumps({
            "schema":SCHEMA,"topology_case":case,
            "generated_only":True,"original_ps3_resources":False,
            "native_gpu_boot_claimed":False,"guest_proof_claimed":False,
            "changed_file":"actor.fojrm","untouched_rear_dds":True,
            "expected_native_marker":MESSAGE,
            "actor_sha256":digest,
            "safe_original_actor_sha256":safe,
        }),encoding="utf-8")
        for phase in ("before","after"):
            (folder/f"actor-{phase}.sha256").write_text(digest+"\n")
        (folder/"native-topology-reject.txt").write_bytes(
            (MESSAGE+"\n").encode("ascii"))
        (folder/"guest.log").write_text("mock, not real guest execution\n")


class Stage275GuestAuditTests(unittest.TestCase):
    def test_classifier_mock_is_not_real_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            result=verify(root)
            self.assertEqual(result["native_unsafe_refusals"],list(CASES))
            self.assertEqual(result["positive_guest_frames"],2)
            self.assertEqual(result["actual_guest_provenance"],
                "requires completed real NeXium CI workflow")

    def test_crossing_and_coplanar_both_unsafe_in_reference_math(self):
        for case in CASES:
            with self.subTest(case=case):
                with self.assertRaises(UnsafeTransparencyOrder):
                    safe_draw_order(rejected_actor(case))

    def test_actual_c11_projected_sort_distinguishes_unsafe_from_invalid(self):
        # Real source modules, not the Python topology oracle: verify both
        # unsafe actors have status UNSAFE=2 (eligible for the opt-in NRO
        # witness) rather than INVALID=1 (which must not write it).
        # The output buffer is transactional on both error paths.
        for compiler in ("gcc","clang"):
            with self.subTest(compiler=compiler),tempfile.TemporaryDirectory() as tmp:
                native=compile_pipeline(compiler,Path(tmp)/"stage275-sort.so")
                camera=Camera(0.,0.,0.,2.,0.,0.,1.,0)
                sections=(Section*3)(
                    Section(0,3,0), Section(3,3,1), Section(6,3,2))
                for case in ("original","reversed",*CASES):
                    with self.subTest(case=case):
                        actor=(rejected_actor(case) if case in CASES
                               else generated_actor(case))
                        projected=(Vertex*9)()
                        batches=(Batch*3)()
                        info=StreamInfo()
                        status=native["project"](
                            Stage274ActualNativeChain.input_vertices(actor),
                            9,sections,3,3,c.byref(camera),1280,720,
                            projected,9,batches,3,c.byref(info))
                        self.assertEqual(status,0)
                        self.assertEqual(
                            (info.vertices_written,info.batches_written),(9,3))
                        order=(U32*3)(999,999,999)
                        native_status=native["sort"](projected,3,order,3)
                        if case in CASES:
                            self.assertEqual(native_status,2)
                            self.assertEqual(tuple(order),(999,999,999))
                        else:
                            self.assertEqual(native_status,0)
                            self.assertEqual(tuple(order),
                                (2,1,0) if case=="original" else (2,0,1))
                # A structurally invalid call is status INVALID=1, never
                # UNSAFE=2, and cannot satisfy the Stage275 witness gate.
                invalid=(U32*3)(999,999,999)
                self.assertEqual(native["sort"](projected,0,invalid,3),1)
                self.assertEqual(tuple(invalid),(999,999,999))

    def test_missing_native_reject_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/"crossing"/"native-topology-reject.txt").unlink()
            with self.assertRaises(ValueError):
                verify(root)

    def test_forged_negative_marker_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/"coplanar"/"native-topology-reject.txt").write_text(
                "FOJ_NATIVE_TOPOLOGY_REJECT_V1 pre_gpu=0 unsafe=1\n")
            with self.assertRaisesRegex(ValueError,"unsafe rejection"):
                verify(root)

    def test_modified_actor_after_guest_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/"crossing"/"actor-after.sha256").write_text("0"*64+"\n")
            with self.assertRaisesRegex(ValueError,"altered actor witness"):
                verify(root)

    def test_sort_marker_contradicts_native_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/"coplanar"/"native-sort-pass.txt").write_bytes(
                b"FOJ_NATIVE_SORT_V1 2,1,0\n")
            with self.assertRaisesRegex(ValueError,"contradictory unsafe"):
                verify(root)

    def test_no_positive_gpu_frames_for_unsafe_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/"crossing"/"gpu-initial.png").write_bytes(b"FAKE")
            with self.assertRaisesRegex(ValueError,"contradictory unsafe"):
                verify(root)

    def test_positive_guest_cannot_emit_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/"original"/"native-topology-reject.txt").write_bytes(
                (MESSAGE+"\n").encode("ascii"))
            with self.assertRaisesRegex(ValueError,"contradictory positive"):
                verify(root)

    def test_missing_gpu_boot_guard_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/"crossing"/"foj-boot-01.txt").write_bytes(b"BOOT")
            with self.assertRaisesRegex(ValueError,"illegal GPU boot"):
                verify(root)


if __name__=="__main__":
    unittest.main()
