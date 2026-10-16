"""Generated, synthetic skeletons and animation clips; no game bytes."""
import math
import struct
import unittest

from tools.decode_rig_banim import (
    RigAnimationError, parse_banim, parse_bmodel_rig, sample_local_pose,
)


def synthetic_rig() -> bytes:
    out = bytearray(b"\x0a" + struct.pack(">H", 2))
    out.extend(struct.pack(">HH4f3f", 0xffff, 0, 0, 0, 0, 1, 0, 0, 0))
    out.extend(struct.pack(">HH4f3f", 0, 4, 0, 0, 0, 1, 0, 2, 0))
    out.extend(b"\x0c")
    return bytes(out)


def synthetic_banim() -> bytes:
    out = bytearray(b"\x0d" + struct.pack("<fIH", 1.0, 2, 0))
    out.extend(b"\x11" + struct.pack("<HH", 0xffff, 2))
    out.extend(b"\x12" + struct.pack("<8f",
                                    0, 0, 0, 0, 1, 0, 0, 0))
    out.extend(b"\x12" + struct.pack("<8f",
                                    1, 0, 0, 1, 0, 2, 0, 0))
    out.extend(b"\x11" + struct.pack("<HH", 0, 1))
    out.extend(b"\x12" + struct.pack("<8f",
                                    0.5, 0, 0, 0, 1, 0, 1, 0))
    out.append(0x13)
    return bytes(out)


class RigAndAnimationFormatTests(unittest.TestCase):
    def test_bmodel_parent_flags_quat_and_translation(self):
        rig = parse_bmodel_rig(synthetic_rig())
        self.assertEqual(rig.summary()["bone_count"], 2)
        self.assertEqual(rig.summary()["root_count"], 1)
        self.assertEqual(rig.bones[0].parent, None)
        self.assertEqual(rig.bones[1].parent, 0)
        self.assertEqual(rig.bones[1].metadata, 4)
        self.assertEqual(rig.bones[1].translation_xyz, (0., 2., 0.))
        self.assertEqual(parse_bmodel_rig(b"\x0c").bones, ())

    def test_animation_structure_and_timeline(self):
        clip = parse_banim(synthetic_banim())
        self.assertEqual(clip.duration, 1.0)
        self.assertEqual(clip.key_count, 3)
        self.assertEqual(clip.summary()["track_count"], 2)
        self.assertEqual(clip.summary()["track_key_counts"], {"1": 1, "2": 1})
        self.assertEqual(clip.tracks[0].parent, None)
        self.assertEqual(clip.tracks[1].parent, 0)
        self.assertEqual(clip.tracks[0].first_time, 0.)
        self.assertEqual(clip.tracks[0].last_time, 1.)
        self.assertFalse(clip.retained)
        self.assertEqual(clip.tracks[0].keys, ())

    def test_slerp_interpolation_and_per_track_clamping(self):
        clip = parse_banim(synthetic_banim(), retain_keys=True)
        mid = sample_local_pose(clip, 0.5)
        self.assertEqual(len(mid), 2)
        self.assertAlmostEqual(mid[0].translation_xyz[0], 1.0)
        self.assertAlmostEqual(mid[0].rotation_xyzw[2], math.sqrt(0.5), places=5)
        self.assertAlmostEqual(mid[0].rotation_xyzw[3], math.sqrt(0.5), places=5)
        self.assertEqual(mid[1].translation_xyz, (0.,1.,0.))
        initial = sample_local_pose(clip, -1.0)
        final = sample_local_pose(clip, 10)
        self.assertEqual(initial[0].translation_xyz, (0.,0.,0.))
        self.assertEqual(final[0].translation_xyz, (2.,0.,0.))
        with self.assertRaisesRegex(RigAnimationError, "Retained keys"):
            sample_local_pose(parse_banim(synthetic_banim()), 0.5)

    def test_one_key_zero_duration_is_valid(self):
        raw = bytearray(b"\x0d" + struct.pack("<fIH", 0., 1, 0))
        raw.extend(b"\x11" + struct.pack("<HH", 0xffff, 1))
        raw.extend(b"\x12" + struct.pack("<8f", 0, 0,0,0,1,0,0,0))
        raw.append(0x13)
        result = parse_banim(bytes(raw), retain_keys=True)
        self.assertEqual(result.duration, 0.)
        self.assertEqual(result.key_count, 1)

    def test_model_rig_malformed_or_invalid_parent(self):
        with self.assertRaises(RigAnimationError):
            parse_bmodel_rig(synthetic_rig()[:-1])
        raw = bytearray(synthetic_rig())
        struct.pack_into(">H", raw, 3 + 32, 3)
        with self.assertRaisesRegex(RigAnimationError, "parent"):
            parse_bmodel_rig(bytes(raw))
        raw = bytearray(synthetic_rig())
        struct.pack_into(">f", raw, 3 + 4, float("nan"))
        with self.assertRaisesRegex(RigAnimationError, "rotation"):
            parse_bmodel_rig(bytes(raw))

    def test_animation_corruption_rejected(self):
        base = synthetic_banim()
        with self.assertRaises(RigAnimationError):
            parse_banim(base[:-1])
        raw = bytearray(base)
        raw[11] = 0xaa
        with self.assertRaisesRegex(RigAnimationError, "track marker"):
            parse_banim(bytes(raw))
        raw = bytearray(base)
        raw[16] = 0xaa
        with self.assertRaisesRegex(RigAnimationError, "keyframe marker"):
            parse_banim(bytes(raw))
        raw = bytearray(base)
        struct.pack_into("<H", raw, 11 + 1, 3)
        with self.assertRaisesRegex(RigAnimationError, "parent"):
            parse_banim(bytes(raw))
        raw = bytearray(base)
        struct.pack_into("<f", raw, 17, float("inf"))
        with self.assertRaisesRegex(RigAnimationError, "time/transform"):
            parse_banim(bytes(raw))


if __name__ == "__main__":
    unittest.main()
