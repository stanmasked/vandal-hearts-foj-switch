"""Private rig/clip inspector is exercised only with invented records."""
import struct
import unittest

from tests.test_decode_rig_banim import synthetic_banim, synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.export_local_rigmesh import pack_rig_mesh
from tools.check_local_rig_pair import inspect_pair


class LocalRigPairTests(unittest.TestCase):
    def setUp(self):
        model = synthetic_complete_model()[:-4] + synthetic_rig()
        self.mesh, self.stats = pack_rig_mesh(model)
        self.anim = synthetic_banim()

    def test_safe_bounded_pair_summary(self):
        report = inspect_pair(self.mesh, self.anim)
        self.assertTrue(report["complete_parent_hierarchy_match"])
        self.assertEqual(report["vertex_count"], 6)
        self.assertEqual(report["weighted_vertex_count"], 3)
        self.assertEqual(report["influence_entries"], 6)
        self.assertEqual(report["section_count"], 2)
        self.assertEqual(report["bone_count"], 2)
        self.assertEqual(report["animation_tracks"], 2)
        self.assertEqual(report["animation_keyframes"], 3)
        self.assertEqual(len(report["local_pose_samples"]), 3)
        self.assertNotIn("original game geometry", str(report))

    def test_rejects_corrupted_skin_weights_and_mismatched_parents(self):
        corrupted = bytearray(self.mesh)
        # First vertex's first bone u32 at header+2bones+2sections+36.
        start = 28 + 64 + 16 + 36
        struct.pack_into("<I", corrupted, start, 4096)
        with self.assertRaisesRegex(ValueError, "influence"):
            inspect_pair(bytes(corrupted), self.anim)
        broken_anim = bytearray(self.anim)
        # Track 1 starts after one track header and two 33-byte keys.
        second_track = 11 + 5 + 66
        struct.pack_into("<H", broken_anim, second_track + 1, 0xffff)
        with self.assertRaisesRegex(ValueError, "hierarchy"):
            inspect_pair(self.mesh, bytes(broken_anim))

    def test_rejects_wrong_magic_and_truncated_file(self):
        with self.assertRaisesRegex(ValueError, "header"):
            inspect_pair(b"BAD!" + self.mesh[4:], self.anim)
        with self.assertRaisesRegex(ValueError, "length"):
            inspect_pair(self.mesh[:-1], self.anim)


if __name__ == "__main__":
    unittest.main()
