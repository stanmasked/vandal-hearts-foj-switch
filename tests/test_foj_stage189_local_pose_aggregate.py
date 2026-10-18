"""Stage 189: only invented BMODEL/BANIM poses, no original game assets."""
from __future__ import annotations

import json
import math
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_foj_stage188_private_topology_audit import (
    animation, model_with_rig, model_without_rig
)
from tests.test_inspect_debug_pkg_assets import make_parts, synthetic_pkg
from tools.foj_stage189_local_pose_aggregate import (
    SCHEMA, _distance, audit_pose_records, audit_split_game
)


def synthetic_zero_duration_clip() -> bytes:
    return (
        b"\x0d" + struct.pack("<fIH", 0.0, 1, 0) +
        b"\x11" + struct.pack("<HH", 0xffff, 1) +
        b"\x12" + struct.pack("<8f", 0, 0, 0, 0, 1, 0, 0, 0) +
        b"\x13"
    )


class Stage189PoseAggregateTests(unittest.TestCase):
    def test_single_topology_pair_returns_aggregate_numeric_bins(self):
        report = audit_pose_records([model_with_rig()], [animation()])
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["bmodels_checked"], 1)
        self.assertEqual(report["models_with_rigs"], 1)
        self.assertEqual(report["banims_checked"], 1)
        self.assertEqual(report["exact_parent_topology_pairs_examined"], 1)
        self.assertEqual(report["banims_with_topology_candidates"], 1)
        self.assertAlmostEqual(
            report["observed_translation_rms_min"], math.sqrt(0.5),
            places=5)
        self.assertEqual(
            report["translation_pairs_below_cumulative_cutoffs"]["1.0"], 1)
        self.assertEqual(
            report["translation_pairs_below_cumulative_cutoffs"]["0.1"], 0)
        self.assertEqual(
            report["rotation_pairs_below_cumulative_cutoffs"]["0.0001"], 1)
        self.assertEqual(
            report["pairs_near_both_at_translation_1_rotation_0_01"], 1)
        self.assertFalse(report["authentic_model_animation_identity_verified"])
        self.assertFalse(report["local_coordinate_spaces_confirmed_comparable"])
        self.assertFalse(report["physical_switch_runtime_verified"])
        output = json.dumps(report, sort_keys=True)
        for prohibited in ("data/actors/", "avatar_idle", "translation_xyz",
                           "rotation_xyzw", "parent_indices"):
            self.assertNotIn(prohibited, output)

    def test_disjoint_multi_root_topology_not_pose_compared(self):
        report = audit_pose_records(
            [model_with_rig(), model_with_rig(second_root=True),
             model_without_rig()],
            [animation(), animation(second_root=True)])
        self.assertEqual(report["exact_parent_topology_pairs_examined"], 2)
        self.assertEqual(report["models_without_rigs"], 1)
        self.assertEqual(report["banims_with_topology_candidates"], 2)

    def test_no_matches_returns_json_null_not_nan(self):
        report = audit_pose_records(
            [model_with_rig()], [animation(second_root=True)])
        self.assertEqual(report["banims_with_topology_candidates"], 0)
        self.assertEqual(report["exact_parent_topology_pairs_examined"], 0)
        self.assertIsNone(report["observed_translation_rms_min"])
        self.assertIsNone(report["observed_rotation_dissimilarity_max"])
        self.assertNotIn("NaN", json.dumps(report, allow_nan=False))

    def test_same_quaternion_orientation_with_opposite_sign(self):
        a = (((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0)),)
        b = (((0.0, 0.0, 0.0, -1.0), (0.0, 0.0, 0.0)),)
        dist, rotation = _distance(a, b)
        self.assertEqual(dist, 0.0)
        self.assertEqual(rotation, 0.0)

    def test_nonzero_rotation_and_translation(self):
        a = (((0.0, 0.0, 0.0, 1.0), (1.0, 2.0, 3.0)),)
        b = (((0.0, 0.0, 1.0, 0.0), (4.0, 6.0, 3.0)),)
        dist, rotation = _distance(a, b)
        self.assertEqual(dist, 5.0)
        self.assertEqual(rotation, 1.0)

    def test_corrupted_inputs_fail_closed(self):
        cases = [
            ([b""], []), ([b"BAD"], []),
            ([model_with_rig()[:-1]], []),
            ([], [b"\x0d" + b"\x00" * 30]),
            ([], [animation()[:-1]]),
            ([model_with_rig()], [None]),
        ]
        for models, clips in cases:
            with self.subTest(n=len(models) + len(clips)):
                with self.assertRaises(ValueError):
                    audit_pose_records(models, clips)

    def test_bounded_pair_evaluation_in_ambiguous_topology(self):
        with patch("tools.foj_stage189_local_pose_aggregate.MAX_EXAMINED_PAIRS", 2):
            with self.assertRaisesRegex(ValueError, "candidate pose"):
                audit_pose_records(
                    [model_with_rig()] * 3,
                    [animation()])

    def test_zero_duration_clip_is_valid_without_match(self):
        report = audit_pose_records([], [synthetic_zero_duration_clip()])
        self.assertEqual(report["banims_checked"], 1)
        self.assertEqual(report["exact_parent_topology_pairs_examined"], 0)

    def test_nested_synthetic_pkg_no_leaked_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            parts = make_parts(directory, synthetic_pkg(with_animation=True))
            report = audit_split_game(parts)
            self.assertEqual(report["bmodels_checked"], 0)
            self.assertEqual(report["banims_checked"], 1)
            self.assertEqual(report["exact_parent_topology_pairs_examined"], 0)
            self.assertNotIn(directory, json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
