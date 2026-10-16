"""No game bytes: generated BMODEL rig -> canonical private FOJRM001 bytes."""
import struct
import unittest

from tests.test_decode_rig_banim import synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.export_local_rigmesh import (
    BONE, HEADER, INFLUENCE, MAGIC, SECTION, VERTEX, pack_rig_mesh,
)


class OriginalRigMeshExportTests(unittest.TestCase):
    def test_multi_section_skinning_payload(self):
        model = synthetic_complete_model()[:-4] + synthetic_rig()
        payload, report = pack_rig_mesh(model)
        self.assertEqual(report["bones"], 2)
        self.assertEqual(report["sections"], 2)
        self.assertEqual(report["vertices"], 6)
        self.assertEqual(report["triangles"], 2)
        self.assertEqual(report["weighted_vertices"], 3)
        self.assertEqual(len(payload), 28 + 2*32 + 2*8 + 6*76)
        self.assertEqual(report["bytes"], len(payload))
        self.assertEqual(HEADER.unpack_from(payload, 0),
                         (MAGIC, 1, 2, 6, 2, 0))
        self.assertEqual(BONE.unpack_from(payload, HEADER.size)[0], -1)
        self.assertEqual(BONE.unpack_from(payload, HEADER.size+BONE.size)[0], 0)
        self.assertEqual(SECTION.unpack_from(
            payload, HEADER.size+2*BONE.size), (0, 3))
        self.assertEqual(SECTION.unpack_from(
            payload, HEADER.size+2*BONE.size+SECTION.size), (3, 3))
        start = HEADER.size + 2*BONE.size + 2*SECTION.size
        data = VERTEX.unpack_from(payload, start)
        self.assertEqual(data[:3], (0, 0, 0))
        self.assertEqual(data[-1], 2)
        self.assertEqual(INFLUENCE.unpack_from(payload, start+VERTEX.size),
                         (0, 0.25))
        self.assertEqual(INFLUENCE.unpack_from(
            payload, start+VERTEX.size+INFLUENCE.size), (1, 0.75))
        rigid = VERTEX.unpack_from(payload, start + 3*76)
        self.assertEqual(rigid[-1], 0)
        self.assertEqual(INFLUENCE.unpack_from(
            payload, start+3*76+VERTEX.size), (0, 0.0))

    def test_requires_rig_and_valid_bound_indices(self):
        with self.assertRaisesRegex(ValueError, "rig"):
            pack_rig_mesh(synthetic_complete_model())
        invalid = bytearray(synthetic_complete_model()[:-4] + synthetic_rig())
        influence = invalid.index(b"\x0f\x00\x06\x00\x02")
        # First influence starts five bytes after header.
        struct.pack_into(">H", invalid, influence+5, 9)
        with self.assertRaisesRegex(ValueError, "Bone index"):
            pack_rig_mesh(bytes(invalid))


if __name__ == "__main__":
    unittest.main()
