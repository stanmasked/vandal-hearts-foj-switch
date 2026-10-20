"""Stage271 native C/Python XY depth-order parity with invented geometry.

Unlike Stage270's 400 depth perturbations at mostly fixed XY positions,
this independently varies triangle positions, aspect, winding, projected
overlap and affine vertex depth. Host-only test, NOT a NeXium guest proof.
"""
from __future__ import annotations
import ctypes
from math import cos, pi, sin
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tools.foj_stage268_transparency_crossing import (
    Triangle, UnsafeTransparencyOrder, pair_relation,
)

ROOT = Path(__file__).resolve().parents[2]
NAME = ("violet", "warm", "cool")


class GPUVertex(ctypes.Structure):
    _fields_ = [(field, ctypes.c_float) for field in
                ("x", "y", "z", "w", "u", "v")]


class GPUBatch(ctypes.Structure):
    _fields_ = [(field, ctypes.c_uint32) for field in
                ("first_vertex", "vertex_count", "texture_index")]


def python_accepts(triangles: tuple[Triangle, ...]) -> bool:
    for i, near in enumerate(triangles):
        for far in triangles[i + 1:]:
            try:
                relation = pair_relation(near, far)
            except UnsafeTransparencyOrder:
                return False
            if relation not in ("disjoint", "b_before_a"):
                return False
    return True


def invented_case(rng: random.Random, index: int):
    # Three nondegenerate triangles, with independently placed/rotated
    # screen projections and randomly reversed winding. XY stays well
    # within [-1,1], while Z stays within [0,1].
    mode = index % 5
    bases = (
        (.82, .53, .20),
        (.25, .74, .40),
        (.56, .56, .22),
        (.52, .52 + 1e-7, .17),
        (.60, .55, .46),
    )[mode]
    vertices = []
    for layer, base in enumerate(bases):
        cx, cy = rng.uniform(-.40, .40), rng.uniform(-.40, .40)
        theta = rng.uniform(-pi, pi)
        points = []
        for corner in range(3):
            angle = theta + corner * 2 * pi / 3 + rng.uniform(-.09, .09)
            radius = rng.uniform(.18, .43)
            x = cx + radius * cos(angle)
            y = cy + radius * sin(angle)
            spread = (.035 if mode == 0 else
                      .025 if mode == 1 else
                      .28 if mode == 2 else
                      0.0 if mode == 3 else .22)
            z = max(.015, min(.985, base + rng.uniform(-spread, spread)))
            points.append((x, y, z))
        if rng.randrange(2):
            points.reverse()
        vertices.extend(GPUVertex(x, y, z, 1.0, 0.0, 0.0)
                        for x, y, z in points)
    return vertices


class XYGeometryParity(unittest.TestCase):
    def test_2000_generated_projected_triangles_against_python(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Path(temporary) / "native-preflight.so"
            subprocess.run([
                "cc", "-std=c11", "-O2", "-Wall", "-Wextra",
                "-Werror", "-pedantic", "-fPIC", "-shared",
                "-Icore", "-Igpu", "gpu/three_layer_preflight.c",
                "-lm", "-o", str(library),
            ], cwd=ROOT, check=True, stdout=subprocess.PIPE,
               stderr=subprocess.PIPE)
            lib = ctypes.CDLL(str(library))
            classify = lib.foj_three_layer_preflight
            classify.argtypes = [
                ctypes.POINTER(GPUVertex), ctypes.c_size_t,
                ctypes.POINTER(GPUBatch), ctypes.c_size_t,
            ]
            classify.restype = ctypes.c_int
            batches = (GPUBatch * 3)(
                GPUBatch(0, 3, 0), GPUBatch(3, 3, 1),
                GPUBatch(6, 3, 2),
            )
            rng = random.Random(271904)
            accepted = rejected = 0
            for index in range(2000):
                native_vertices = invented_case(rng, index)
                triangles = tuple(
                    Triangle(
                        NAME[layer],
                        tuple((float(v.x), float(v.y), float(v.z))
                              for v in native_vertices[3*layer:3*layer+3]),
                    )
                    for layer in range(3)
                )
                expected = python_accepts(triangles)
                answer = classify(
                    (GPUVertex * 9)(*native_vertices), 9, batches, 3,
                )
                self.assertIn(answer, (0, 2),
                              f"Valid test geometry unexpectedly invalid at {index}")
                self.assertEqual(
                    answer == 0, expected,
                    f"Case {index}, mode {index % 5}: "
                    f"native status {answer}, Python accepts {expected}, "
                    f"triangles={triangles}",
                )
                if expected:
                    accepted += 1
                else:
                    rejected += 1
            self.assertGreater(accepted, 80)
            self.assertGreater(rejected, 80)


if __name__ == "__main__":
    unittest.main()
