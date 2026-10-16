"""Tests generated from small invented triangles, never original game meshes."""
import io
import math
from pathlib import Path
import struct
import tempfile
import unittest

from tools.decode_bmodel_geometry import (
    BModelError, decode_first_shape, write_local_obj,
)


def synthetic_mesh() -> bytes:
    name = b"syntheticShape_0"
    b = bytearray(b"\x0b\x09\x00\x01\x01\x20\x00")
    b.append(len(name))
    b.extend(name)
    count = 6

    def start(tag, n):
        b.extend(struct.pack(">BH", tag, n))

    def vectors(vs, dims):
        for v in vs:
            assert len(v) == dims
            b.extend(struct.pack(">" + "f" * dims, *v))

    positions = [
        (0.,0.,0.), (2.,0.,0.), (0.,2.,0.),
        (2.,0.,0.), (2.,2.,0.), (0.,2.,0.),
    ]
    uvs = [
        (0.,0.), (1.,0.), (0.,1.),
        (1.,0.), (1.,1.), (0.,1.),
    ]
    start(0x02, count)
    vectors(positions, 3)
    start(0x05, count)
    b.extend(b"\x00\x03")
    vectors(uvs, 2)
    start(0x10, count)
    vectors([(0.,0.,1.)] * count, 3)
    start(0x15, count // 3)
    vectors([(0.,0.,1.)] * (count // 3), 3)
    start(0x04, count)
    for i in range(count):
        b.extend(struct.pack(">H", i))
    b.extend(b"\x0f\x00\x00")  # unknown later shape material/etc.
    return bytes(b)


class BModelTriangleMeshTests(unittest.TestCase):
    def test_complete_first_shape(self):
        shape = decode_first_shape(synthetic_mesh())
        self.assertEqual(shape.name, "syntheticShape_0")
        self.assertEqual(shape.indices, tuple(range(6)))
        self.assertEqual(shape.vertices[4], (2.,2.,0.))
        self.assertEqual(shape.uvs[4], (1.,1.))
        self.assertEqual(shape.normals[4], (0.,0.,1.))
        report = shape.summary()
        self.assertEqual(report["triangle_count"], 2)
        self.assertEqual(report["vertex_count"], 6)
        self.assertEqual(report["bounds_xyz"]["maximum"], [2.,2.,0.])
        self.assertEqual(report["uv_bounds"]["maximum"], [1.,1.])
        self.assertLess(report["maximum_nonzero_normal_length_error"], 1e-6)
        self.assertEqual(report["zero_length_vertex_normals"], 0)
        self.assertEqual(shape.section_end, len(synthetic_mesh()) - 3)

    def test_local_obj_no_overwrite_and_uv_flip(self):
        shape = decode_first_shape(synthetic_mesh())
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "synthetic.obj"
            write_local_obj(shape, out, flip_v=True)
            text = out.read_text("utf-8")
            self.assertEqual(text.count("\nv "), 6)
            self.assertEqual(text.count("\nvt "), 6)
            self.assertEqual(text.count("\nvn "), 6)
            self.assertEqual(text.count("\nf "), 2)
            self.assertIn("vt 0 1\n", text)
            self.assertIn("f 1/1/1 2/2/2 3/3/3", text)
            self.assertIn("f 4/4/4 5/5/5 6/6/6", text)
            with self.assertRaises(FileExistsError):
                write_local_obj(shape, out)
            with self.assertRaises(ValueError):
                write_local_obj(shape, Path(directory) / "not_obj.txt")

    def test_truncated_and_bad_magic(self):
        data = synthetic_mesh()
        with self.assertRaises(BModelError):
            decode_first_shape(data[:20])
        with self.assertRaises(BModelError):
            decode_first_shape(b"XX" + data[2:])
        with self.assertRaises(BModelError):
            decode_first_shape(data[:-10])

    def test_reject_invalid_index(self):
        data = bytearray(synthetic_mesh())
        struct.pack_into(">H", data, len(data) - 5, 55)
        with self.assertRaisesRegex(BModelError, "index"):
            decode_first_shape(bytes(data))

    def test_reject_nonfinite_vertex(self):
        data = bytearray(synthetic_mesh())
        vertex_start = 8 + len(b"syntheticShape_0") + 3
        struct.pack_into(">f", data, vertex_start, math.inf)
        with self.assertRaisesRegex(BModelError, "Non-finite"):
            decode_first_shape(bytes(data))

    def test_zero_normal_allowed_as_seen_in_original_models(self):
        data = bytearray(synthetic_mesh())
        n = 6
        normal_start = (8 + len(b"syntheticShape_0")
                        + 3 + n*12 + 5 + n*8 + 3)
        struct.pack_into(">3f", data, normal_start, 0., 0., 0.)
        shape = decode_first_shape(bytes(data))
        self.assertEqual(shape.summary()["zero_length_vertex_normals"], 1)
        self.assertLess(
            shape.summary()["maximum_nonzero_normal_length_error"], 1e-6
        )

    def test_opt_in_reverse_winding(self):
        shape = decode_first_shape(synthetic_mesh())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mesh.obj"
            write_local_obj(shape, path, reverse_winding=True)
            self.assertIn("f 1/1/1 3/3/3 2/2/2", path.read_text())
            self.assertIn("f 4/4/4 6/6/6 5/5/5", path.read_text())

    def test_reject_nonunit_normal(self):
        data = bytearray(synthetic_mesh())
        shape = decode_first_shape(bytes(data))
        # Find the normal section without relying on a hardcoded source offset.
        n = len(shape.vertices)
        normals_start = (8 + len(b"syntheticShape_0")
                         + 3 + n*12 + 5 + n*8 + 3)
        struct.pack_into(">3f", data, normals_start, 5., 5., 5.)
        with self.assertRaisesRegex(BModelError, "Normal"):
            decode_first_shape(bytes(data))

    def test_reject_unknown_uv_prefix_and_triangle_count(self):
        data = bytearray(synthetic_mesh())
        n = 6
        uv_tag = 8 + len(b"syntheticShape_0") + 3 + n*12
        data[uv_tag + 3] = 0xFF
        with self.assertRaisesRegex(BModelError, "UV array prefix"):
            decode_first_shape(bytes(data))
        data[uv_tag + 3] = 0
        face_tag = uv_tag + 5 + n*8 + 3 + n*12
        data[face_tag + 2] = 3
        with self.assertRaisesRegex(BModelError, "count mismatch"):
            decode_first_shape(bytes(data))


if __name__ == "__main__":
    unittest.main()
