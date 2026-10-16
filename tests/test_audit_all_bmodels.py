"""Aggregate full FoJ model audits against generated dummy PSARC resources."""
import unittest

from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.audit_all_bmodels import audit_model_records


class FullBModelAuditTests(unittest.TestCase):
    def setUp(self):
        self.manifest = [
            "data/actors/npc/a.bmodel",
            "data/actors/prop/b.bmodel",
            "data/actors/npc/shared.tga",
            "data/actors/prop/shared.tga",
            "data/actors/npc/arm.tga",
        ]
        self.fixture = synthetic_complete_model()

    def test_models_shapes_skin_materials_and_texture_resolution(self):
        result = audit_model_records(self.manifest, lambda name: self.fixture)
        self.assertEqual(result["manifest_bmodel_count"], 2)
        self.assertEqual(result["inspected_count"], 2)
        self.assertEqual(result["success_count"], 2)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["total_shapes"], 4)
        self.assertEqual(result["total_triangles"], 4)
        self.assertEqual(result["models_with_skinning"], 2)
        self.assertEqual(result["shapes_with_skinning"], 2)
        self.assertEqual(result["total_bone_influences"], 12)
        self.assertEqual(result["material_entries"], 4)
        self.assertEqual(result["texture_references"], 4)
        self.assertEqual(result["unique_texture_basenames"], 2)
        self.assertEqual(result["texture_path_resolution"]["same_directory"], 3)
        self.assertEqual(result["texture_path_resolution"]["unique_basename"], 1)
        self.assertEqual(result["footer_tags_uninterpreted"], {"0x0c": 2})

    def test_corrupt_model_does_not_fake_success(self):
        report = audit_model_records(
            self.manifest,
            lambda name: self.fixture if "/npc/" in name else b"invalid"
        )
        self.assertEqual(report["success_count"], 1)
        self.assertEqual(report["error_count"], 1)
        self.assertEqual(report["inspected_count"], 2)

    def test_bounded_sample_count_and_limit(self):
        report = audit_model_records(
            self.manifest, lambda _: self.fixture, max_models=1
        )
        self.assertEqual(report["success_count"], 1)
        self.assertEqual(report["inspected_count"], 1)
        for value in (0, 3000):
            with self.assertRaisesRegex(ValueError, "limit"):
                audit_model_records(self.manifest, lambda _: self.fixture,
                                    max_models=value)


if __name__ == "__main__":
    unittest.main()
