"""Host-only Stage271 negative-fixture tests, not evidence of guest execution."""
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools.foj_stage271_generated_negative_sd import (
    CASES, rejected_actor, install_rejected, VERTEX_OFFSET, VERTEX_SIZE,
)
from tools.foj_stage269_guarded_scene import guard_three_layer_mesh
from tools.foj_stage268_transparency_crossing import UnsafeTransparencyOrder


class NegativeGuestFixtures(unittest.TestCase):
    def test_every_negative_actor_rejected_by_independent_host_guard(self):
        for case in CASES:
            with self.subTest(case=case):
                actor=rejected_actor(case)
                self.assertEqual(actor[:8],b"FOJRM001")
                self.assertEqual(len(actor),28+32+3*8+9*76)
                with self.assertRaises(UnsafeTransparencyOrder):
                    guard_three_layer_mesh(actor)

    def test_distinct_case_changes_only_expected_z_bytes(self):
        from tools.foj_stage267_generated_multiblend_sd import generated_three_layer_mesh
        source=generated_three_layer_mesh()
        for case in CASES:
            actual=rejected_actor(case)
            self.assertEqual(len(source),len(actual))
            changed=[i for i in range(len(actual)) if source[i]!=actual[i]]
            legal=set()
            for slot in (0,1):
                for vertex in range(3):
                    pos=VERTEX_OFFSET+(3*slot+vertex)*VERTEX_SIZE+8
                    legal.update(range(pos,pos+4))
            self.assertTrue(changed)
            self.assertTrue(set(changed).issubset(legal))

    def test_unsupported_case_no_files_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"absent"
            with self.assertRaises(ValueError):
                install_rejected(root,Path(tmp)/"shaders","other")
            self.assertFalse(root.exists())

    def test_rejects_existing_private_data_root_without_modification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"existing"
            root.mkdir()
            (root/"keep").write_bytes(b"PRIVATE")
            with self.assertRaises(ValueError):
                install_rejected(root,Path(tmp)/"shaders","crossing")
            self.assertEqual((root/"keep").read_bytes(),b"PRIVATE")

    def test_rejected_case_does_not_write_native_receipt_in_python(self):
        # Actor generator and path construction alone cannot establish
        # the native marker. The NRO must write it when run in NeXium.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"new"
            # Stage267 installer requires real UAM DKSH; mock only that
            # installer to check the unsafe fixture isn't a forged receipt.
            with patch("tools.foj_stage271_generated_negative_sd.install_three_layer") as mock:
                mock.return_value={"generated_only":True}
                # Missing actor is refused; no marker can exist.
                with self.assertRaises(ValueError):
                    install_rejected(root,Path(tmp),"crossing")
                self.assertFalse(root.exists())
            self.assertFalse((root/"sdmc/switch/foj/gpu/foj-native-unsafe-reject.txt").exists())

    def test_boot_marker_is_not_in_any_negative_actor(self):
        for case in CASES:
            with self.subTest(case=case):
                self.assertNotIn(b"FOJ_NATIVE_UNSAFE_REJECT_V1",rejected_actor(case))

    def test_three_cases_are_unique(self):
        self.assertEqual(len({rejected_actor(case) for case in CASES}),3)


if __name__=="__main__":
    unittest.main()
