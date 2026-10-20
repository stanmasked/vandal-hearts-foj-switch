"""Stage272 randomized compiled C11 versus independent Python DAG oracle.

Generated-only orthographic triangle geometry. No actual NeXium rendering.
"""
from __future__ import annotations
import ctypes
from math import cos, sin, pi
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from tools.foj_stage268_transparency_crossing import (
    Triangle, UnsafeTransparencyOrder, plan_back_to_front,
)

ROOT=Path(__file__).resolve().parents[2]
class Vertex(ctypes.Structure):
    _fields_=[(name,ctypes.c_float) for name in ("x","y","z","w","u","v")]


class HostSortParity(unittest.TestCase):
    def test_1000_randomized_triangle_dags(self):
        with tempfile.TemporaryDirectory() as tmp:
            libpath=Path(tmp)/"libfoj_alpha_sort.so"
            subprocess.run([
                "cc","-std=c11","-O2","-Wall","-Wextra",
                "-Werror","-pedantic","-shared","-fPIC",
                "-Icore","-Igpu","gpu/transparency_sort.c",
                "-lm","-o",str(libpath),
            ],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            lib=ctypes.CDLL(str(libpath))
            native=lib.foj_alpha_sort_back_to_front
            native.argtypes=[ctypes.POINTER(Vertex),ctypes.c_size_t,
                             ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t]
            native.restype=ctypes.c_int
            rng=random.Random(272002)
            safe=unsafe=0
            for case in range(1000):
                count=1+case%8
                verts=[]
                triangles=[]
                for i in range(count):
                    cx=rng.uniform(-.55,.55)
                    cy=rng.uniform(-.55,.55)
                    rotation=rng.uniform(-pi,pi)
                    depth=rng.uniform(.12,.88)
                    span=.03 if case%3==0 else .23
                    poly=[]
                    for j in range(3):
                        angle=rotation+2*pi*j/3+rng.uniform(-.11,.11)
                        radius=rng.uniform(.12,.35)
                        x=cx+radius*cos(angle)
                        y=cy+radius*sin(angle)
                        z=max(.01,min(.99,depth+rng.uniform(-span,span)))
                        poly.append(Vertex(x,y,z,1.,0.,0.))
                    if rng.randrange(2):
                        poly.reverse()
                    verts.extend(poly)
                    triangles.append(Triangle(f"T{i:02d}",tuple(
                        (float(v.x),float(v.y),float(v.z)) for v in poly)))
                array=(Vertex*len(verts))(*verts)
                out=(ctypes.c_uint32*count)(*([0xAAAAAAAA]*count))
                status=native(array,count,out,count)
                try:
                    order=plan_back_to_front(tuple(triangles))
                except UnsafeTransparencyOrder:
                    self.assertEqual(status,2,
                       f"Case {case}: Python unsafe; native={status}")
                    self.assertTrue(all(i==0xAAAAAAAA for i in out),
                       f"Case {case}: output mutated on refusal")
                    unsafe+=1
                else:
                    self.assertEqual(status,0,
                       f"Case {case}: Python safe; native={status}")
                    expected=tuple(int(name[1:]) for name in order)
                    self.assertEqual(tuple(out),expected,
                       f"Case {case}: different back-to-front draw order")
                    safe+=1
            self.assertGreater(safe,50)
            self.assertGreater(unsafe,50)

    def test_equal_depth_pair_is_unsafe_transactionally(self):
        with tempfile.TemporaryDirectory() as tmp:
            libpath=Path(tmp)/"sort.so"
            subprocess.run(["cc","-std=c11","-shared","-fPIC","-Icore","-Igpu",
                            "gpu/transparency_sort.c","-lm","-o",str(libpath)],
                           cwd=ROOT,check=True)
            lib=ctypes.CDLL(str(libpath))
            fn=lib.foj_alpha_sort_back_to_front
            fn.argtypes=[ctypes.POINTER(Vertex),ctypes.c_size_t,
                         ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t]
            fn.restype=ctypes.c_int
            xy=((-0.25,-0.25),(.25,-0.25),(0,.25))
            verts=[Vertex(x,y,.5,1.,0.,0.) for _ in range(2) for x,y in xy]
            output=(ctypes.c_uint32*2)(47,53)
            self.assertEqual(fn((Vertex*6)(*verts),2,output,2),2)
            self.assertEqual(tuple(output),(47,53))


if __name__=="__main__":
    unittest.main()
