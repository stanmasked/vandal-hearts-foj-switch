"""Stage270 cross-check the compiled C11 NRO guard against Stage268 geometry oracle.

The test compiles *actual* gpu/three_layer_preflight.c as a tiny host shared
library and exercises all three material pairs on deterministic, invented
triangles. It never launches or fakes an emulator.
"""
from __future__ import annotations
import ctypes
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tools.foj_stage268_transparency_crossing import (
    Triangle, UnsafeTransparencyOrder, pair_relation,
)

REPO = Path(__file__).resolve().parents[2]
BATCHES = ((0,3,0),(3,3,1),(6,3,2))
NAMES = ("violet","warm","cool")


class GPUVertex(ctypes.Structure):
    _fields_=[(x,ctypes.c_float) for x in ("x","y","z","w","u","v")]


class GPUBatch(ctypes.Structure):
    _fields_=[(x,ctypes.c_uint32) for x in
              ("first_vertex","vertex_count","texture_index")]


def expected_safe(triangles):
    for i,a in enumerate(triangles):
        for b in triangles[i+1:]:
            try:
                relation=pair_relation(a,b)
            except UnsafeTransparencyOrder:
                return False
            if relation not in ("disjoint","b_before_a"):
                return False
    return True


class CAgainstPythonParity(unittest.TestCase):
    def test_generated_triangles_and_400_perturbations(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/"native_guard.so"
            subprocess.run(["cc","-std=c11","-O2","-Wall","-Wextra",
                "-Werror","-pedantic","-fPIC","-shared","-Icore","-Igpu",
                "gpu/three_layer_preflight.c","-lm","-o",str(binary)],
                cwd=REPO,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            lib=ctypes.CDLL(str(binary))
            fn=lib.foj_three_layer_preflight
            fn.argtypes=[ctypes.POINTER(GPUVertex),ctypes.c_size_t,
                         ctypes.POINTER(GPUBatch),ctypes.c_size_t]
            fn.restype=ctypes.c_int
            batches=(GPUBatch*3)(*(GPUBatch(*b) for b in BATCHES))
            rng=random.Random(270)
            xys=(
                ((-.76,-.50),(.34,-.50),(-.21,.69)),
                ((-.76,-.50),(.34,-.50),(-.21,.69)),
                ((-.35,-.50),(.75,-.50),(.20,.69)),
            )
            for iteration in range(400):
                verts=[]
                triangles=[]
                for layer,base in enumerate((.85,.55,.20)):
                    triangle=[]
                    for x,y in xys[layer]:
                        perturb = rng.uniform(-.46,.46) if iteration else 0.
                        z = max(.01,min(.99,base+perturb))
                        v=GPUVertex(x,y,z,1.,0.,0.)
                        verts.append(v)
                        # Python gets exactly the single-precision floats
                        # the native guard will read (no format mismatch).
                        triangle.append((float(v.x),float(v.y),float(v.z)))
                    triangles.append(Triangle(NAMES[layer],tuple(triangle)))
                expected=expected_safe(tuple(triangles))
                native=fn((GPUVertex*9)(*verts),9,batches,3)
                self.assertEqual(native==0,expected,
                    f"case {iteration}: expected={expected}, C={native}")
                self.assertIn(native,(0,2))


if __name__=="__main__":
    unittest.main()
