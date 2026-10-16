"""Synthetic aggregate test for all-files rig + animation scanner."""
import struct
import unittest

from tests.test_decode_rig_banim import synthetic_banim, synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.audit_rig_anims import audit_rig_animation_records


def zero_duration_clip() -> bytes:
    raw = bytearray(b"\x0d" + struct.pack("<fIH", 0., 1, 0))
    raw.extend(b"\x11" + struct.pack("<HH", 0xffff, 1))
    raw.extend(b"\x12" + struct.pack("<8f", 0, 0, 0, 0, 1, 0, 0, 0))
    raw.append(0x13)
    return bytes(raw)


class FullRigAuditTests(unittest.TestCase):
    def test_generated_game_archive_audit(self):
        model_rig = synthetic_complete_model()[:-4] + synthetic_rig()
        model_static = synthetic_complete_model(skin=False)[:-4] + b"\x0c"
        output = audit_rig_animation_records(
            [model_rig, model_static],
            [synthetic_banim(), zero_duration_clip()],
        )
        self.assertEqual(output["bmodel_file_count"], 2)
        self.assertEqual(output["models_with_rig"], 1)
        self.assertEqual(output["models_with_skin_weights"], 1)
        self.assertEqual(output["total_bones"], 2)
        self.assertEqual(output["rig_root_counts_by_model"], {"1": 1})
        self.assertEqual(output["bone_metadata_field_counts"], {"0": 1, "4": 1})
        self.assertEqual(output["banim_file_count"], 2)
        self.assertEqual(output["banim_track_count"], 3)
        self.assertEqual(output["banim_total_keyframes"], 4)
        self.assertEqual(output["zero_duration_clips"], 1)

    def test_rejects_bad_keyframe_and_rig(self):
        malformed = bytearray(synthetic_banim())
        malformed[-1] = 0
        with self.assertRaises(ValueError):
            audit_rig_animation_records([], [bytes(malformed)])
        with self.assertRaises(ValueError):
            audit_rig_animation_records([b"not-a-model"], [])


if __name__ == "__main__":
    unittest.main()
