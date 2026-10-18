"""Stage 194: fully generated test fixtures, including compiled native C session."""
from __future__ import annotations

import contextlib
from io import StringIO
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from tests.test_decode_rig_banim import synthetic_banim, synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.export_local_rigmesh import pack_rig_mesh
from tools.check_local_rig_clip_set import inspect_clip_set, main

ROOT = Path(__file__).resolve().parents[1]


class PrivateRigClipSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        model = synthetic_complete_model()[:-4] + synthetic_rig()
        cls.rig, _ = pack_rig_mesh(model)
        cls.primary = synthetic_banim()
        # Distinct but structurally compatible: change first key translation
        # while preserving key layout, valid units and ordered parents.
        secondary = bytearray(cls.primary)
        # BANIM header 11, first track header 5, first key 0x12 + 4-byte
        # time + 16-byte quaternion => 32-bit XYZ starts at offset 37.
        struct.pack_into("<f", secondary, 11+5+1+4+16, 0.25)
        cls.secondary = bytes(secondary)

    def test_two_compatible_clips_safe_summary(self):
        report = inspect_clip_set(self.rig,self.primary,self.secondary)
        self.assertTrue(report["primary_hierarchy_match"])
        self.assertTrue(report["secondary_hierarchy_match"])
        self.assertTrue(report["optional_secondary_accepted"])
        self.assertEqual(report["bone_count"],2)
        self.assertFalse(report["original_ps3_actor_clip_binding_verified"])
        self.assertNotIn("pose", str(report).lower())
        self.assertNotIn("translation", str(report).lower())
        self.assertNotIn("asset", str(report).lower())

    def test_legacy_one_clip_contract(self):
        report = inspect_clip_set(self.rig,self.primary)
        self.assertFalse(report["optional_secondary_accepted"])
        self.assertIsNone(report["secondary_track_count"])

    def test_identical_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError,"distinct"):
            inspect_clip_set(self.rig,self.primary,self.primary)

    def test_second_bad_topology_rejected(self):
        broken=bytearray(self.secondary)
        # Track 1 starts after header + first track's two 33-byte keys.
        struct.pack_into("<H",broken,11+5+2*33+1,0xffff)
        with self.assertRaises(ValueError):
            inspect_clip_set(self.rig,self.primary,bytes(broken))

    def test_bad_primary_rejected(self):
        with self.assertRaises(ValueError):
            inspect_clip_set(self.rig,b"not a BANIM",self.secondary)

    def test_corrupt_mesh_rejected(self):
        with self.assertRaises(ValueError):
            inspect_clip_set(b"invalid rig",self.primary,self.secondary)

    def test_cli_path_does_not_leak_on_error(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            path=folder/"confidential-game-resource.banim"
            path.write_bytes(b"invalid")
            captured=StringIO()
            with contextlib.redirect_stderr(captured):
                status=main([str(path),str(path)])
            self.assertEqual(status,2)
            self.assertNotIn(str(path),captured.getvalue())
            self.assertNotIn("confidential",captured.getvalue())

    def test_cli_success_has_only_research_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            (folder/"r.fojrm").write_bytes(self.rig)
            (folder/"a.banim").write_bytes(self.primary)
            (folder/"b.banim").write_bytes(self.secondary)
            output=StringIO()
            with contextlib.redirect_stdout(output):
                status=main([str(folder/"r.fojrm"),str(folder/"a.banim"),
                             "--secondary",str(folder/"b.banim")])
            self.assertEqual(status,0)
            self.assertIn('"optional_secondary_accepted": true',output.getvalue())
            self.assertNotIn(str(folder),output.getvalue())

    def test_production_c_actor_session_host_contract(self):
        cc=shutil.which("cc")
        if not cc:
            self.skipTest("No host C compiler available")
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"actor-check"
            sources=[
                "tests/test_foj_stage194_actor_session.c",
                "core/rigged_actor_session.c",
                "core/anim_player.c",
                "core/rigmesh_io.c",
                "core/banim_core.c",
                "core/skeletal_skin.c",
            ]
            subprocess.run(
                [cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",
                 "-pedantic","-Icore",*sources,"-lm","-o",str(output)],
                cwd=ROOT,check=True,capture_output=True,text=True,timeout=30,
            )
            result=subprocess.run(
                [str(output)],cwd=ROOT,check=True,capture_output=True,
                text=True,timeout=20,
            )
            self.assertIn("STAGE194 ACTOR SESSION PASS",result.stdout)


if __name__ == "__main__":
    unittest.main()
