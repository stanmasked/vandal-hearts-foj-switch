"""Stage273 host tests: synthetic fixtures/classifier only, never guest proof."""
from pathlib import Path
import ctypes
import json
import struct
import subprocess
import tempfile
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage273_dynamic_gpu_sd import (
    CASES, BACK_TO_FRONT, VERTEX_START,VERTEX_STRIDE,
    generated_actor,safe_draw_order,expected_rgb,install_dynamic,
)
from tools.foj_stage267_generated_multiblend_sd import (
    generated_three_layer_mesh, expected_rgb as stage267_rgb,
)
from tools.foj_stage269_guarded_scene import guard_three_layer_mesh
from tools.foj_stage268_transparency_crossing import (
    Triangle, pair_relation, plan_back_to_front, UnsafeTransparencyOrder,
)
from tools.foj_stage273_dynamic_gpu_check import inspect,verify
from tools.foj_stage267_gpu_three_layer_check import PROBES

class DynamicSceneTests(unittest.TestCase):
    def test_distinct_compositing_and_earlier_baseline(self):
        self.assertEqual(expected_rgb("original"),(111,100,162))
        self.assertEqual(expected_rgb("reversed"),(146,96,119))
        self.assertEqual(expected_rgb("original"),stage267_rgb("both-half"))
        self.assertNotEqual(expected_rgb("original"),expected_rgb("reversed"))

    def test_native_target_order_from_true_mesh_xyz(self):
        for case in CASES:
            with self.subTest(case=case):
                self.assertEqual(safe_draw_order(generated_actor(case)),
                                 BACK_TO_FRONT[case])
        self.assertEqual(guard_three_layer_mesh(generated_actor("original")),
                         ("cool","warm","violet"))
        with self.assertRaises(UnsafeTransparencyOrder):
            guard_three_layer_mesh(generated_actor("reversed"))

    def test_swapped_fixture_modifies_only_depth_floats(self):
        original=generated_actor("original")
        reversed_actor=generated_actor("reversed")
        self.assertEqual(original,generated_three_layer_mesh())
        changed={i for i,(a,b) in enumerate(zip(original,reversed_actor)) if a!=b}
        legal=set()
        for slot in (0,1):
            for vertex in range(3):
                index=VERTEX_START+(3*slot+vertex)*VERTEX_STRIDE+8
                legal.update(range(index,index+4))
        self.assertTrue(changed)
        self.assertTrue(changed.issubset(legal))

    def test_real_native_projection_then_c_planner_for_both_fojrm_cases(self):
        # The *actual* core/gpu_vertex_stream.c projection, not a Python
        # approximation of XY/depth transformation, feeds the exact C11
        # GPU sort module. Both original and swapped FOJRM001 fixture XYZ
        # and UV bytes are passed unaltered to the compiled C functions.
        class TexturedVertex(ctypes.Structure):
            _fields_=[(n,ctypes.c_float) for n in ("x","y","z","u","v")]
        class Section(ctypes.Structure):
            _fields_=[("first_vertex",ctypes.c_size_t),
                      ("vertex_count",ctypes.c_size_t),
                      ("texture_index",ctypes.c_uint)]
        class Camera(ctypes.Structure):
            _fields_=[(n,ctypes.c_float) for n in
                      ("center_x","center_y","center_z",
                       "extent","yaw","pitch","zoom")]+[
                       ("flip_v",ctypes.c_int)]
        class StreamInfo(ctypes.Structure):
            _fields_=[("vertices_written",ctypes.c_size_t),
                      ("batches_written",ctypes.c_size_t),
                      ("camera_depth_min",ctypes.c_float),
                      ("camera_depth_max",ctypes.c_float)]
        class Vertex(ctypes.Structure):
            _fields_=[(field,ctypes.c_float) for field in
                      ("x","y","z","w","u","v")]
        class Batch(ctypes.Structure):
            _fields_=[(field,ctypes.c_uint32) for field in
                      ("first_vertex","vertex_count","texture_index")]

        with tempfile.TemporaryDirectory() as tmp:
            lib=Path(tmp)/"projection-and-sort.so"
            repo=Path(__file__).resolve().parents[2]
            subprocess.run([
                "cc","-std=c11","-O2","-Wall","-Wextra",
                "-Werror","-pedantic","-shared","-fPIC",
                "-Icore","-Igpu","core/gpu_vertex_stream.c",
                "gpu/transparency_sort.c","-lm","-o",str(lib),
            ],cwd=repo,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            native=ctypes.CDLL(str(lib))
            project=native.foj_gpu_prepare_stream
            project.argtypes=[
                ctypes.POINTER(TexturedVertex),ctypes.c_size_t,
                ctypes.POINTER(Section),ctypes.c_size_t,
                ctypes.c_size_t,ctypes.POINTER(Camera),
                ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(Vertex),
                ctypes.c_size_t,ctypes.POINTER(Batch),ctypes.c_size_t,
                ctypes.POINTER(StreamInfo)]
            project.restype=ctypes.c_int
            classifier=native.foj_alpha_sort_back_to_front
            classifier.argtypes=[
                ctypes.POINTER(Vertex),ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t]
            classifier.restype=ctypes.c_int

            sections=(Section*3)(
                Section(0,3,0),Section(3,3,1),Section(6,3,2))
            camera=Camera(0.,0.,0.,2.,0.,0.,1.,0)
            for case in CASES:
                with self.subTest(case=case):
                    mesh=generated_actor(case)
                    source=(TexturedVertex*9)(*(TexturedVertex(
                        *struct.unpack_from(
                            "<5f",mesh,VERTEX_START+i*VERTEX_STRIDE))
                        for i in range(9)))
                    projected=(Vertex*9)()
                    batches=(Batch*3)()
                    info=StreamInfo()
                    self.assertEqual(
                        project(source,9,sections,3,3,
                                ctypes.byref(camera),1280,720,
                                projected,9,batches,3,ctypes.byref(info)),
                        0)
                    self.assertEqual((info.vertices_written,
                                      info.batches_written),(9,3))
                    self.assertEqual(
                        [(b.first_vertex,b.vertex_count,b.texture_index)
                         for b in batches],
                        [(0,3,0),(3,3,1),(6,3,2)])
                    self.assertTrue(all(v.w==1.0 and 0.0<v.z<1.0
                                        for v in projected))
                    order=(ctypes.c_uint32*3)(999,999,999)
                    self.assertEqual(classifier(projected,3,order,3),0)
                    self.assertEqual(tuple(order),BACK_TO_FRONT[case])

    def test_three_pairwise_safe_intersections_can_form_unsafe_cycle(self):
        # Three planar translucent triangles overlap at three distinct
        # places: A near B, B near C, C near A. The depth comparisons
        # never cross within each pair, yet no global order exists.
        raw=(
            ((.88058,-.42220,.92917),(.46793,.58045,.47462),
             (-.19407,-.27824,.05000)),
            ((.09299,-.06395,.05000),(.04929,.66650,.05000),
             (-.56145,.26344,.77722)),
            ((.22444,-.58653,.45352),(-.15052,.24749,.05000),
             (-.68532,-.49425,.05000)),
        )
        a,b,c=tuple(Triangle(name,coords) for name,coords
                    in zip(("A","B","C"),raw))
        self.assertEqual(pair_relation(a,b),"b_before_a")
        self.assertEqual(pair_relation(b,c),"b_before_a")
        self.assertEqual(pair_relation(a,c),"a_before_b")
        with self.assertRaisesRegex(
                UnsafeTransparencyOrder,"Cyclic triangle depth precedence"):
            plan_back_to_front((a,b,c))

    def test_bad_case_and_preexisting_private_root_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"private"
            root.mkdir()
            (root/"keep").write_bytes(b"ORIGINAL")
            with self.assertRaises(ValueError):
                install_dynamic(root,Path(temp),"original")
            self.assertEqual((root/"keep").read_bytes(),b"ORIGINAL")
            missing=Path(temp)/"missing"
            with self.assertRaises(ValueError):
                install_dynamic(missing,Path(temp),"wrong")
            self.assertFalse(missing.exists())

    def test_truncated_and_bad_header_not_sorted(self):
        source=generated_actor("original")
        for corrupted in (source[:-1],b"BAD!" + source[4:]):
            with self.assertRaises(ValueError):
                safe_draw_order(corrupted)

    @staticmethod
    def make_png(path:Path,case:str,background):
        image=Image.new("RGB",(1280,720),background)
        pen=ImageDraw.Draw(image)
        for name,(x,y) in PROBES.items():
            color=(21,202,219) if name=="rear_only" else expected_rgb(case)
            pen.rectangle((x-8,y-8,x+8,y+8),fill=color)
        image.save(path)

    def test_host_classifier_accepts_both_expected_rgb_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for case in CASES:
                path=root/(case+".png")
                self.make_png(path,case,(55,31,67))
                self.assertEqual(inspect(path,case)["overlap"]["matching_pixels"],121)

    def test_host_classifier_rejects_wrong_alpha_order(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"wrong.png"
            self.make_png(path,"original",(55,31,67))
            with self.assertRaises(ValueError):
                inspect(path,"reversed")

    @classmethod
    def synthesized_receipts(cls,root:Path,duplicated:bool=False):
        """Only classifier fixtures; not evidence that NeXium executed."""
        for case in CASES:
            folder=root/case
            folder.mkdir()
            (folder/"generated-input.json").write_text(json.dumps({
                "schema":"foj.stage273.dynamic_gpu_sort.v1",
                "scenario":case,
                "generated_only":True,
                "guest_proof_claimed":False,
                "expected_native_pass_order":list(BACK_TO_FRONT[case]),
                "expected_overlap_rgb":list(expected_rgb(case)),
            }))
            native = "FOJ_NATIVE_SORT_V1 " + ",".join(
                map(str,BACK_TO_FRONT[case])) + "\n"
            (folder/"native-sort-pass.txt").write_bytes(native.encode("ascii"))
            cls.make_png(folder/"gpu-initial.png",case,(55,31,67))
            later=(55,31,67) if duplicated else (112,145,110)
            cls.make_png(folder/"gpu-later.png",case,later)

    def test_host_only_synthetic_accepted_receipts_do_not_claim_guest(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.synthesized_receipts(root)
            result=verify(root)
            self.assertEqual(result["verified_guest_frames"],4)
            self.assertEqual(set(result["cases"]),set(CASES))
            for case in CASES:
                self.assertTrue(result["cases"][case][
                    "native_guest_sort_receipt_checked"])
            self.assertEqual(result["actual_guest_provenance"],
                             "requires real NeXium GitHub Actions workflow")

    def test_wrong_native_sort_marker_rejected_despite_valid_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.synthesized_receipts(root)
            (root/"reversed"/"native-sort-pass.txt").write_bytes(
                b"FOJ_NATIVE_SORT_V1 2,1,0\n")
            with self.assertRaisesRegex(ValueError,"native guest sort receipt"):
                verify(root)

    def test_missing_native_sort_marker_rejected_despite_valid_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.synthesized_receipts(root)
            (root/"original"/"native-sort-pass.txt").unlink()
            with self.assertRaisesRegex(ValueError,"native guest sort receipt"):
                verify(root)

    def test_duplicate_captures_do_not_constitute_guest_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            self.synthesized_receipts(root,duplicated=True)
            with self.assertRaises(ValueError):
                verify(root)


if __name__=="__main__":
    unittest.main()
