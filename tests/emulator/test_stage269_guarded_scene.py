"""Stage269 generated-actor safety gate regression tests."""
import struct
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from tools.foj_stage267_generated_multiblend_sd import generated_three_layer_mesh
from tools.foj_stage268_transparency_crossing import UnsafeTransparencyOrder
from tools.foj_stage269_guarded_scene import guard_three_layer_mesh, install_guarded

OFFSET = 28 + 32 + 3*8
STRIDE = 76


def change_z(raw: bytes, slot: int, values) -> bytes:
    buf = bytearray(raw)
    for idx,value in enumerate(values):
        struct.pack_into("<f",buf,OFFSET + (slot*3+idx)*STRIDE + 8,value)
    return bytes(buf)


class GeneratedPreflightTests(unittest.TestCase):
    def test_real_generated_actor_has_expected_fixed_order(self):
        self.assertEqual(guard_three_layer_mesh(generated_three_layer_mesh()),
                         ("cool","warm","violet"))

    def test_crossing_violet_warm_is_rejected(self):
        source=generated_three_layer_mesh()
        # Warm spans both sides of constant violet depth over the same XY.
        bad=change_z(source,1,(-.3,.9,.08))
        with self.assertRaises(UnsafeTransparencyOrder):
            guard_three_layer_mesh(bad)

    def test_reversed_fixed_order_is_rejected(self):
        source=generated_three_layer_mesh()
        bad=change_z(source,0,(-.75,-.75,-.75))
        with self.assertRaises(UnsafeTransparencyOrder):
            guard_three_layer_mesh(bad)

    def test_nan_is_rejected(self):
        source=generated_three_layer_mesh()
        with self.assertRaises(ValueError):
            guard_three_layer_mesh(change_z(source,1,(float("nan"),.08,.08)))

    def test_truncated_and_modified_sections_rejected(self):
        source=generated_three_layer_mesh()
        with self.assertRaises(ValueError): guard_three_layer_mesh(source[:-1])
        bad=bytearray(source)
        struct.pack_into("<I",bad,60,1)
        with self.assertRaises(ValueError): guard_three_layer_mesh(bytes(bad))

    def test_crossing_rejected_without_creating_root(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)/"must_not_exist"
            bad=change_z(generated_three_layer_mesh(),1,(-.3,.9,.08))
            with patch("tools.foj_stage269_guarded_scene.generated_three_layer_mesh",
                       return_value=bad):
                with self.assertRaises(UnsafeTransparencyOrder):
                    install_guarded(root,Path(dirname)/"shaders","both-half")
            self.assertFalse(root.exists())

    def test_existing_root_is_never_mutated(self):
        with tempfile.TemporaryDirectory() as dirname:
            root=Path(dirname)/"existing"
            root.mkdir()
            (root/"sentinel").write_bytes(b"keep private")
            with self.assertRaises(ValueError):
                install_guarded(root,Path(dirname),"both-half")
            self.assertEqual((root/"sentinel").read_bytes(),b"keep private")


if __name__=="__main__":
    unittest.main()
