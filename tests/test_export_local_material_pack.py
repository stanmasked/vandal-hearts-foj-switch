"""Test deterministic local FOJMAT01 plans with generated BMODEL only."""
import struct
import unittest

from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.export_local_material_pack import MAGIC, make_material_plan


class OriginalMaterialPackTests(unittest.TestCase):
    def setUp(self):
        self.model = synthetic_complete_model()
        self.path = "data/actors/npc/invented.bmodel"
        self.manifest = [
            "data/actors/prop/shared.tga",
            "data/actors/npc/shared.tga",
            "data/actors/npc/arm.tga",
        ]

    def test_prefers_same_directory_and_preserves_section_order(self):
        table, paths = make_material_plan(self.model, self.path, self.manifest)
        self.assertEqual(table[:8], MAGIC)
        self.assertEqual(struct.unpack_from("<II", table, 8), (2, 2))
        self.assertEqual(struct.unpack_from("<II", table, 16), (0, 1))
        self.assertEqual(paths, [
            "data/actors/npc/shared.tga", "data/actors/npc/arm.tga"
        ])

    def test_disallows_ambiguous_basename_without_local_resolution(self):
        with self.assertRaisesRegex(ValueError, "unresolved"):
            make_material_plan(
                self.model, "data/actors/other/invented.bmodel", self.manifest
            )

    def test_missing_material_image_rejected(self):
        with self.assertRaisesRegex(ValueError, "unresolved"):
            make_material_plan(
                self.model, self.path, self.manifest[:-1]
            )


if __name__ == "__main__":
    unittest.main()
