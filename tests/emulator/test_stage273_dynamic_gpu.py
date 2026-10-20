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
from tools.foj_stage268_transparency_crossing import UnsafeTransparencyOrder
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

    def test_compiled_c_planner_matches_generated_actor_orders(self):
        # Exact generated vertex XYZ, normalized into the same monotonic
        # [0,1] research depth and orthographic XY transform used by NRO.
        # This tests actual C sorting, not only the Python name DAG.
        class Vertex(ctypes.Structure):
            _fields_=[(field,ctypes.c_float) for field in
                      ("x","y","z","w","u","v")]
        with tempfile.TemporaryDirectory() as tmp:
            lib=Path(tmp)/"dynamic-sort.so"
            repo=Path(__file__).resolve().parents[2]
            subprocess.run([
                "cc","-std=c11","-O2","-Wall","-Wextra",
                "-Werror","-pedantic","-shared","-fPIC",
                "-Icore","-Igpu","gpu/transparency_sort.c",
                "-lm","-o",str(lib),
            ],cwd=repo,check=True)
            binary=ctypes.CDLL(str(lib))
            classifier=binary.foj_alpha_sort_back_to_front
            classifier.argtypes=[
                ctypes.POINTER(Vertex),ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t]
            classifier.restype=ctypes.c_int
            for case in CASES:
                with self.subTest(case=case):
                    actor=generated_actor(case)
                    raw=[struct.unpack_from("<3f",actor,VERTEX_START+
                         i*VERTEX_STRIDE) for i in range(9)]
                    depths=[z for _,_,z in raw]
                    lo,hi=min(depths),max(depths)
                    vertices=(Vertex*9)(*(Vertex(
                        x*.4725,y*.84,.01+.98*(z-lo)/(hi-lo),1,0,0)
                        for x,y,z in raw))
                    order=(ctypes.c_uint32*3)(999,999,999)
                    self.assertEqual(classifier(vertices,3,order,3),0)
                    self.assertEqual(tuple(order),BACK_TO_FRONT[case])

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

    def test_duplicate_captures_do_not_constitute_guest_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
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
                self.make_png(folder/"gpu-initial.png",case,(55,31,67))
                self.make_png(folder/"gpu-later.png",case,(55,31,67))
            with self.assertRaises(ValueError):
                verify(root)


if __name__=="__main__":
    unittest.main()
