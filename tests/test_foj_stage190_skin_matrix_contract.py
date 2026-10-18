"""Independent synthetic Python quaternion oracle for real C skinning code.

This is a convention-testing harness, NOT an original PS3 FoJ pose decoder.
The reference composes quaternion+translation pairs geometrically and
rotates canonical axes to construct palette rows; the production C code
independently multiplies 3x4 matrices and inverts rigid transforms.
"""
from __future__ import annotations

import math
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = (0.0, 0.0, 0.0, 1.0)
Q = math.sqrt(0.5)


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw*bx + ax*bw + ay*bz - az*by,
        aw*by - ax*bz + ay*bw + az*bx,
        aw*bz + ax*by - ay*bx + az*bw,
        aw*bw - ax*bx - ay*by - az*bz,
    )


def rotate(q, point):
    # Unlike C's explicit rotation-matrix coefficients, the oracle
    # uses q*(pure-vector quaternion)*conjugate(q).
    length = math.sqrt(sum(x*x for x in q))
    normalized = tuple(x/length for x in q)
    inverse = (-normalized[0], -normalized[1], -normalized[2],
               normalized[3])
    pq = (point[0], point[1], point[2], 0.0)
    result = qmul(qmul(normalized, pq), inverse)
    return result[:3]


def add(a, b):
    return tuple(x+y for x, y in zip(a, b, strict=True))


def neg(a):
    return tuple(-x for x in a)


def bone(parent, tx, ty, tz, q=IDENTITY):
    return (parent, q, (tx, ty, tz))


def vertex(x, y, z, *influences):
    return ((x, y, z), tuple(influences))


def fixtures():
    b0 = [
        bone(-1, 10, 0, 0),
        bone(0, 0, 2, 0),
        bone(-1, -6, 0, 0),
    ]
    a0 = b0.copy()
    v0 = [
        vertex(11, 2, 0, (1, 1)),
        vertex(-5, 0, 0, (2, 1)),
        vertex(0, 7, 0),
        vertex(11, 2, 0, (0, 0.5), (1, 0.5)),
    ]

    b1 = b0[:2]
    a1 = [b1[0], bone(0, 0, 2, 0, (0, 0, Q, Q))]
    v1 = [
        vertex(11, 2, 0, (1, 1)),
        vertex(11, 2, 0, (0, 0.5), (1, 0.5)),
        vertex(11, 2, 0, (0, 1)),
    ]

    b2 = [
        bone(-1, 2, 1, 0),
        bone(0, 0, 2, 0),
        bone(-1, -3, 0, 1),
    ]
    a2 = [
        bone(-1, 2, 1, 0, (0, 0, Q, Q)),
        bone(0, 0, 3, 0),
        bone(-1, -2, 0, 1),
    ]
    v2 = [
        vertex(2, 3, 0, (1, 1)),
        vertex(-3, 0, 1, (2, 1)),
        vertex(5, 5, 0, (0, 0.25), (1, 0.75)),
    ]

    b3 = [bone(-1, 2, -3, 4)]
    a3 = [bone(-1, 2, -3, 4, (0, 0, 0, -1))]
    v3 = [vertex(3, -3, 4, (0, 1)), vertex(2, -2, 4)]

    b4 = [
        bone(-1, 5, 2, 0),
        bone(0, 2, 0, 0),
        bone(1, 0, 1, 0),
    ]
    a4 = [
        bone(-1, 5, 2, 0, (0, Q, 0, Q)),
        bone(0, 2, 0, 0, (0, 0, -Q, Q)),
        bone(1, 0, 1, 1, (Q, 0, 0, Q)),
    ]
    v4 = [
        vertex(8, 3, 0, (2, 1)),
        vertex(9, 3, 1, (0, 0.2), (1, 0.3), (2, 0.5)),
        vertex(-1, 1, 4),
    ]
    return [
        ("bind_multiroot", b0, a0, v0),
        ("child_z90", b1, a1, v1),
        ("two_roots_parent_z90", b2, a2, v2),
        ("opposite_quaternion_sign", b3, a3, v3),
        ("three_bone_xyz_rotations", b4, a4, v4),
    ]


def composed_world(bones):
    world = []
    for index, (parent, q, t) in enumerate(bones):
        if parent >= index or parent < -1:
            raise ValueError("Non-ancestral bone parent")
        if parent == -1:
            world.append((q, t))
        else:
            ancestor_q, ancestor_t = world[parent]
            world.append((qmul(ancestor_q, q),
                          add(ancestor_t, rotate(ancestor_q, t))))
    return world


def expected(bind, animated, vertices):
    if len(bind) != len(animated) or any(
        x[0] != y[0] for x, y in zip(bind, animated, strict=True)
    ):
        raise ValueError("Parent hierarchy mismatch")
    bind_world = composed_world(bind)
    anim_world = composed_world(animated)
    palette = []
    for (bq, bt), (aq, at) in zip(bind_world, anim_world, strict=True):
        b_inverse = (-bq[0], -bq[1], -bq[2], bq[3])
        transform_q = qmul(aq, b_inverse)
        transform_t = add(at, neg(rotate(transform_q, bt)))
        palette.append((transform_q, transform_t))

    matrices = []
    basis = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    for q, t in palette:
        columns = [rotate(q, axis) for axis in basis]
        matrices.append(tuple(
            value for row in range(3)
            for value in (columns[0][row], columns[1][row],
                          columns[2][row], t[row])
        ))

    outputs = []
    for position, influences in vertices:
        if not influences:
            outputs.append(position)
            continue
        out = [0.0, 0.0, 0.0]
        for index, weight in influences:
            q, t = palette[index]
            moved = add(rotate(q, position), t)
            for axis in range(3):
                out[axis] += weight * moved[axis]
        outputs.append(tuple(out))
    return matrices, outputs


def read_probe(text):
    result = {}
    lines = iter(text.splitlines())
    for header in lines:
        parts = header.split()
        if len(parts) != 4 or parts[0] != "CASE" or parts[1] in result:
            raise ValueError("Unexpected native C probe section")
        _, name, bones, vertices = parts
        try:
            n, v = int(bones), int(vertices)
        except ValueError as exc:
            raise ValueError("Invalid native probe section counts") from exc
        if not 1 <= n <= 3 or not 1 <= v <= 4:
            raise ValueError("Invalid native C probe dimensions")
        def line(expected_tag, count):
            pieces = next(lines).split()
            if len(pieces) != count + 1 or pieces[0] != expected_tag:
                raise ValueError("Invalid native C probe data record")
            numbers = tuple(float(number) for number in pieces[1:])
            if not all(math.isfinite(number) for number in numbers):
                raise ValueError("Nonfinite native probe result")
            return numbers
        matrices = [line("M", 12) for _ in range(n)]
        outputs = [line("V", 3) for _ in range(v)]
        if next(lines) != "END":
            raise ValueError("Native case missing END")
        result[name] = matrices, outputs
    return result


class Stage190IndependentSkinningContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tempdir.cleanup)
        executable = str(Path(cls.tempdir.name) / "stage190-probe")
        subprocess.run([
            "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
            "-pedantic", "-Icore",
            "tools/foj_stage190_skin_matrix_probe.c",
            "core/skeletal_skin.c", "core/banim_core.c", "-lm",
            "-o", executable,
        ], cwd=ROOT, capture_output=True, text=True, check=True)
        process = subprocess.run([executable], cwd=ROOT, capture_output=True,
                                 text=True, check=True, timeout=12)
        cls.text_output = process.stdout
        cls.actual = read_probe(process.stdout)

    def assert_coords_match(self, actual, expected_values):
        self.assertEqual(len(actual), len(expected_values))
        for row, (seen, predicted) in enumerate(
            zip(actual, expected_values, strict=True)
        ):
            self.assertEqual(len(seen), len(predicted))
            for col, (got, want) in enumerate(
                zip(seen, predicted, strict=True)
            ):
                self.assertAlmostEqual(
                    got, want, delta=0.0003,
                    msg=f"Row {row}, component {col}: native vs oracle")

    def test_all_five_cases_have_independent_matrix_and_vertex_agreement(self):
        self.assertEqual(set(self.actual),
                         {name for name, *_ in fixtures()})
        for name, bind, animated, vertices in fixtures():
            with self.subTest(case=name):
                expected_matrices, expected_vertices = expected(
                    bind, animated, vertices)
                got_matrices, got_vertices = self.actual[name]
                self.assert_coords_match(got_matrices, expected_matrices)
                self.assert_coords_match(got_vertices, expected_vertices)

    def test_child_rotation_has_known_analytic_result(self):
        _, bind, animated, vertices = fixtures()[1]
        _, positions = expected(bind, animated, vertices)
        self.assert_coords_match(
            positions, ((10.0, 3.0, 0.0),
                        (10.5, 2.5, 0.0),
                        (11.0, 2.0, 0.0)))

    def test_all_bind_palette_matrices_are_exact_identity(self):
        matrices, _ = self.actual["bind_multiroot"]
        identity = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)
        self.assert_coords_match(matrices, [identity]*3)

    def test_quaternion_sign_does_not_change_skinning(self):
        matrices, xyz = self.actual["opposite_quaternion_sign"]
        self.assert_coords_match(
            matrices, [(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)])
        self.assert_coords_match(xyz, [(3, -3, 4), (2, -2, 4)])

    def test_three_bone_chain_preserves_unweighted_vertex(self):
        _, positions = self.actual["three_bone_xyz_rotations"]
        self.assert_coords_match([positions[-1]], [(-1, 1, 4)])

    def test_invalid_native_probe_data_rejected(self):
        with self.assertRaises((ValueError, StopIteration)):
            read_probe(self.text_output.replace("END", "BAD", 1))
        with self.assertRaises((ValueError, StopIteration)):
            read_probe(self.text_output.replace("CASE", "STUFF", 1))
        with self.assertRaises((ValueError, StopIteration)):
            read_probe(self.text_output.replace("M ", "M nan ", 1))
        with self.assertRaises((ValueError, StopIteration)):
            read_probe(self.text_output.rsplit("END", 1)[0])


if __name__ == "__main__":
    unittest.main()
