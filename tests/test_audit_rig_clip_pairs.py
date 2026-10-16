"""Rig/clip pairing regression fixtures contain generated hierarchies only."""
import unittest

from tests.test_decode_rig_banim import synthetic_banim, synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.audit_rig_clip_pairs import (
    compare_layouts, rig_parent_layout, clip_parent_layout,
)


class BoneHierarchyMatchTests(unittest.TestCase):
    def test_decode_generated_real_format_parent_arrays(self):
        model = synthetic_complete_model()[:-4] + synthetic_rig()
        self.assertEqual(rig_parent_layout(model), (-1, 0))
        self.assertEqual(clip_parent_layout(synthetic_banim()), (-1, 0))

    def test_exact_hierarchy_match_and_distinct_ambiguous_models(self):
        rigs = {
            "actorA.bmodel": (-1, 0),
            "actorB.bmodel": (-1, 0),
            "beast.bmodel": (-1, 0, 1),
            "statue.bmodel": (),
        }
        clips = {
            "idle.banim": (-1, 0),
            "hit.banim": (-1, 0),
            "beast_walk.banim": (-1, 0, 1),
            "not_same_hierarchy.banim": (-1, -1, 1),
        }
        result = compare_layouts(rigs, clips)
        self.assertEqual(result["rigged_models"], 3)
        self.assertEqual(result["models_with_matching_clip_hierarchy"], 3)
        self.assertEqual(result["clips_with_matching_model_hierarchy"], 3)
        self.assertEqual(result["distinct_matching_parent_hierarchies"], 2)
        self.assertEqual(result["candidate_model_clip_pairs"], 5)
        self.assertEqual(result["unmatched_clip_names"], ["not_same_hierarchy.banim"])
        self.assertEqual(result["unmatched_clip_track_counts"], {
            "not_same_hierarchy.banim": 3
        })
        self.assertEqual(result["model_bone_count_distribution"], {2: 2, 3: 1})

    def test_equal_bone_count_not_sufficient(self):
        report = compare_layouts({"mesh.bmodel": (-1, 0, 1)},
                                 {"wrong.banim": (-1, -1, 1)})
        self.assertEqual(report["candidate_model_clip_pairs"], 0)
        self.assertEqual(report["clips_with_matching_model_hierarchy"], 0)

    def test_limits(self):
        with self.assertRaisesRegex(ValueError, "safety"):
            compare_layouts({str(i): (-1,) for i in range(2001)}, {})


if __name__ == "__main__":
    unittest.main()
