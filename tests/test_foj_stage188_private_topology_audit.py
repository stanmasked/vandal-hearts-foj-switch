"""Stage 188: structural topology matching only, using invented PS3 fixtures."""
from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tests.test_decode_rig_banim import synthetic_banim, synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tests.test_inspect_debug_pkg_assets import make_parts, synthetic_pkg
from tools.foj_stage188_private_topology_audit import (
    SCHEMA, MAX_MODELS, MAX_ANIMATIONS,
    audit_topology_records, audit_split_game
)


def model_with_rig(*, second_root=False) -> bytes:
    footer = bytearray(synthetic_rig())
    if second_root:
        # The second 32-byte bone record begins after 0A + N(u16) + bone0.
        struct.pack_into(">H", footer, 3 + 32, 0xffff)
    return synthetic_complete_model()[:-4] + footer


def model_without_rig() -> bytes:
    return synthetic_complete_model()[:-4] + b"\x0c"


def animation(*, second_root=False) -> bytes:
    blob = bytearray(synthetic_banim())
    if second_root:
        # Next track: first 11-byte header + 5-byte track header + 2 keys.
        struct.pack_into("<H", blob, 11 + 5 + 66 + 1, 0xffff)
    return bytes(blob)


class TestStage188CandidateAudit(unittest.TestCase):
    def test_aggregate_counts_count_only_candidates_and_ambiguity(self):
        report = audit_topology_records(
            [model_with_rig(), model_with_rig(second_root=True),
             model_without_rig()],
            [animation(), animation(), animation(second_root=True)]
        )
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["bmodel_records_checked"], 3)
        self.assertEqual(report["bmodel_rigged"], 2)
        self.assertEqual(report["bmodel_without_rig"], 1)
        self.assertEqual(report["banim_records_checked"], 3)
        self.assertEqual(report["same_bone_track_count_candidate_pairs"], 6)
        self.assertEqual(report["exact_parent_topology_candidate_pairs"], 3)
        self.assertEqual(report["candidate_pairs_rejected_by_parent_topology"], 3)
        self.assertEqual(report["matching_hierarchy_shape_classes"], 2)
        self.assertEqual(report["unique_one_model_one_animation_shape_classes"], 1)
        self.assertEqual(report["ambiguous_hierarchy_shape_classes"], 1)
        self.assertEqual(report["candidate_pairs_in_ambiguous_classes"], 2)
        self.assertEqual(report["model_records_with_at_least_one_topology_candidate"], 2)
        self.assertEqual(report["animation_records_with_at_least_one_topology_candidate"], 3)
        self.assertFalse(report["engine_binding_verified"])
        encoded = json.dumps(report)
        self.assertNotIn("data/actors", encoded)
        self.assertNotIn("parent_indices", encoded)
        self.assertNotIn("avatar", encoded)

    def test_same_bone_count_but_different_hierarchy_is_not_a_match(self):
        report = audit_topology_records(
            [model_with_rig()], [animation(second_root=True)])
        self.assertEqual(report["same_bone_track_count_candidate_pairs"], 1)
        self.assertEqual(report["exact_parent_topology_candidate_pairs"], 0)
        self.assertEqual(report["rigged_models_without_topology_candidate"], 1)
        self.assertEqual(report["animations_without_topology_candidate"], 1)

    def test_model_and_animation_with_no_rigs_or_tracks(self):
        report = audit_topology_records([model_without_rig()], [])
        self.assertEqual(report["bmodel_without_rig"], 1)
        self.assertEqual(report["banim_records_checked"], 0)
        self.assertEqual(report["exact_parent_topology_candidate_pairs"], 0)
        self.assertEqual(report["distinct_model_hierarchy_shapes"], 0)
        self.assertEqual(report["matching_hierarchy_shape_classes"], 0)

    def test_invalid_asset_data_rejected(self):
        cases = [
            ([b""], []),
            ([b"\x00"], []),
            ([model_with_rig()[:-1]], []),
            ([], [b"\x0d" + bytes(32)]),
            ([], [animation()[:-1]]),
            ([model_with_rig()], [b"BAD" + animation()[3:]]),
            ([model_with_rig()], [None]),
        ]
        for models, clips in cases:
            with self.subTest(size=len(models) + len(clips)):
                with self.assertRaises(ValueError):
                    audit_topology_records(models, clips)

    def test_count_limits_rejected_before_expensive_parse(self):
        with self.assertRaises(ValueError):
            audit_topology_records([model_without_rig()] * (MAX_MODELS + 1), [])
        with self.assertRaises(ValueError):
            audit_topology_records([], [animation()] * (MAX_ANIMATIONS + 1))

    def test_synthetic_private_package_end_to_end_with_no_rigs(self):
        # The existing nested synthetic PKG contains one valid BANIM and
        # zero full BMODEL files. This exercises streamed local archive reads.
        with tempfile.TemporaryDirectory() as directory:
            parts = make_parts(directory, synthetic_pkg(with_animation=True))
            result = audit_split_game(parts)
            self.assertEqual(result["bmodel_records_checked"], 0)
            self.assertEqual(result["banim_records_checked"], 1)
            self.assertEqual(result["animations_without_topology_candidate"], 1)
            self.assertNotIn(directory, json.dumps(result))


if __name__ == "__main__":
    unittest.main()
