"""Generated multi-shape model fixtures, no original PS3 assets in CI."""
from __future__ import annotations

import math
import struct
import tempfile
from pathlib import Path
import unittest

from tools.inspect_complete_bmodel import (
    ModelFormatError, decode_model, resolve_textures, write_full_obj,
)


def synthetic_complete_model(*, skin: bool = True) -> bytes:
    data = bytearray(b"\x0b\x09\x00\x02")

    def u16(n):
        data.extend(struct.pack(">H", n))

    def string16(text):
        value = text.encode("utf-8")
        u16(len(value))
        data.extend(value)

    def shape(name: str, material: str, with_skin: bool):
        data.extend(b"\x01\x20\x00")
        value = name.encode()
        data.append(len(value))
        data.extend(value)
        n = 3
        vectors = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ]
        data.append(0x02)
        u16(n)
        for v in vectors:
            data.extend(struct.pack(">fff", *v))
        data.append(0x05)
        u16(n)
        data.extend(b"\x00\x03")
        for uv in ((0.,0.),(1.,0.),(0.,1.)):
            data.extend(struct.pack(">ff", *uv))
        data.append(0x10)
        u16(n)
        for _ in range(n):
            data.extend(struct.pack(">fff", 0, 0, 1))
        data.append(0x15)
        u16(1)
        data.extend(struct.pack(">fff", 0, 0, -1))
        data.append(0x04)
        u16(n)
        data.extend(struct.pack(">HHH", 0, 1, 2))
        if with_skin:
            data.append(0x0F)
            u16(n * 2)
            u16(2)
            for _ in range(n):
                data.extend(struct.pack(">HfHf", 0, 0.25, 1, 0.75))
        data.append(0x14)
        string16(material)
        data.append(0x21)
        data.extend(struct.pack(">6f", 0, 0, 0, 1, 1, 0))

    shape("headShape_0", "body_mat", skin)
    data.append(0x07)
    shape("armShape_0", "arm_mat", False)
    data.append(0x07)
    for mat, tex in (("body_mat", "shared.tga"),
                     ("arm_mat", "arm.tga")):
        data.append(0x06)
        string16(mat)
        u16(1)
        string16(tex)
    data.extend(b"\x0c\x12\x34\x56")  # opaque final record
    return bytes(data)


class CompleteBModelTests(unittest.TestCase):
    def test_multi_shape_and_material_bundles(self):
        record = decode_model(synthetic_complete_model())
        self.assertEqual(len(record.shapes), 2)
        self.assertEqual(record.report()["triangle_count"], 2)
        self.assertEqual(record.report()["vertex_count"], 6)
        self.assertEqual(record.shapes[0].name, "headShape_0")
        self.assertEqual(record.shapes[0].influences_per_vertex, 2)
        self.assertEqual(record.shapes[0].bone_index_max, 1)
        self.assertEqual(record.shapes[1].influences_per_vertex, 0)
        self.assertEqual(record.shapes[1].material, "arm_mat")
        self.assertEqual(record.footer_tag, 0x0C)
        self.assertEqual(record.materials[0].texture_names, ("shared.tga",))
        self.assertEqual(record.materials[1].texture_names, ("arm.tga",))
        self.assertGreater(record.shapes[1].xyz_offset, record.shapes[0].xyz_offset)

    def test_same_directory_wins_and_else_ambiguity(self):
        materials = decode_model(synthetic_complete_model()).materials
        manifest = [
            "data/actors/prop/shared.tga",
            "data/actors/npc/shared.tga",
            "data/actors/npc/arm.tga",
        ]
        mapping = resolve_textures("data/actors/npc/hero.bmodel", materials,
                                   manifest)
        self.assertEqual(mapping["body_mat"][0]["resolution"], "same_directory")
        self.assertEqual(mapping["body_mat"][0]["path"],
                         "data/actors/npc/shared.tga")
        self.assertEqual(mapping["arm_mat"][0]["resolution"], "same_directory")
        wrong_directory = resolve_textures("data/actors/other/hero.bmodel",
                                            materials, manifest)
        self.assertEqual(wrong_directory["body_mat"][0]["resolution"], "ambiguous")
        self.assertIsNone(wrong_directory["body_mat"][0]["path"])

    def test_full_export_to_local_obj(self):
        data = synthetic_complete_model()
        model = decode_model(data)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "all_shapes.obj"
            write_full_obj(data, model, output, reverse_winding=True,
                           flip_v=True)
            text = output.read_text("utf-8")
            self.assertEqual(text.count("\no "), 2)
            self.assertEqual(text.count("\nusemtl "), 2)
            self.assertEqual(text.count("\nv "), 6)
            self.assertEqual(text.count("\nvt "), 6)
            self.assertEqual(text.count("\nvn "), 6)
            self.assertIn("f 1/1/1 3/3/3 2/2/2", text)
            self.assertIn("f 4/4/4 6/6/6 5/5/5", text)
            self.assertIn("usemtl body_mat", text)
            self.assertIn("usemtl arm_mat", text)
            with self.assertRaises(FileExistsError):
                write_full_obj(data, model, output)
            with self.assertRaises(ValueError):
                write_full_obj(data, model, Path(directory) / "bad.zip")

    def test_single_shape_skinless(self):
        data = synthetic_complete_model(skin=False)
        record = decode_model(data)
        self.assertEqual(record.report()["skinned_shape_count"], 0)

    def test_reject_modified_skin_weights(self):
        data = bytearray(synthetic_complete_model())
        # Locate the first bone/influence block and corrupt a fraction.
        where = data.index(b"\x0f\x00\x06\x00\x02")
        struct.pack_into(">f", data, where + 5 + 2, 0.9)
        with self.assertRaisesRegex(ModelFormatError, "weights do not sum"):
            decode_model(bytes(data))

    def test_reject_bad_footer_and_truncation(self):
        data = synthetic_complete_model()
        with self.assertRaises(ModelFormatError):
            decode_model(data[:-2]) if False else decode_model(data[:-5])
        changed = bytearray(data)
        changed[-4] = 0xEE
        with self.assertRaisesRegex(ModelFormatError, "footer"):
            decode_model(bytes(changed))

    def test_reject_invalid_index_count(self):
        data = bytearray(synthetic_complete_model())
        # Indices tag follows the sole face normal; locate full tag and corrupt.
        idx = data.index(b"\x04\x00\x03\x00\x00\x00\x01\x00\x02")
        data[idx + 8] = 99
        with self.assertRaisesRegex(ModelFormatError, "nonsequential"):
            decode_model(bytes(data))

    def test_reject_nonfinite_bbox(self):
        data = bytearray(synthetic_complete_model())
        tag = data.index(b"\x21" + struct.pack(">6f", 0,0,0,1,1,0))
        struct.pack_into(">f", data, tag + 1, math.inf)
        with self.assertRaisesRegex(ModelFormatError, "bounding"):
            decode_model(bytes(data))


if __name__ == "__main__":
    unittest.main()
