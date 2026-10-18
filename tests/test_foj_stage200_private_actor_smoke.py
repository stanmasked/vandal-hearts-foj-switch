"""Stage 200: independently invented on-disk rig/BANIM end-to-end smoke.

Exercises EXACT user SD hierarchy, production native C parsers, actor session,
CPU weighted skinning and real PPM wireframe outputs. All inputs synthetic.
No original PS3 game files or captures leave the user's own computer.
"""
from __future__ import annotations

import contextlib
from io import StringIO
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

from tests.test_decode_rig_banim import synthetic_banim, synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.export_local_rigmesh import pack_rig_mesh
from tools.foj_stage200_prepare_private_sd import (
    SCHEMA, prepare, main as prepare_main
)

ROOT=Path(__file__).resolve().parents[1]


class Stage200ActorSdSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        model=synthetic_complete_model()[:-4]+synthetic_rig()
        cls.mesh,_=pack_rig_mesh(model)
        cls.first=synthetic_banim()
        extra=bytearray(cls.first)
        # Change invented secondary root translation; same full hierarchy.
        struct.pack_into("<f",extra,11+5+1+4+16,.25)
        cls.secondary=bytes(extra)

        cls.temp_build=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp_build.cleanup)
        cls.compiler=shutil.which("cc")
        cls.executable=Path(cls.temp_build.name)/"actor-host-smoke"
        if cls.compiler:
            subprocess.run([
                cls.compiler,"-std=c11","-O2","-Wall","-Wextra",
                "-Werror","-pedantic","-Icore",
                "tools/foj_stage200_actor_host_smoke.c",
                "core/rigged_actor_session.c","core/anim_player.c",
                "core/rigmesh_io.c","core/banim_core.c",
                "core/skeletal_skin.c","core/obj_wireframe.c",
                "-lm","-o",str(cls.executable),
            ],cwd=ROOT,check=True,capture_output=True,text=True,timeout=40)

    def assets(self,folder):
        folder=Path(folder)
        path1=folder/"private_rig.fojrm"
        path2=folder/"private_clip_a.banim"
        path3=folder/"private_clip_b.banim"
        path1.write_bytes(self.mesh)
        path2.write_bytes(self.first)
        path3.write_bytes(self.secondary)
        return path1,path2,path3

    def test_private_sd_exact_layout_dual_clip(self):
        with tempfile.TemporaryDirectory() as tmp:
            first,anim,alt=self.assets(tmp)
            sd=Path(tmp)/"new-private-sd"
            result=prepare(sd,first,anim,alt)
            self.assertEqual(result["schema"],SCHEMA)
            self.assertEqual(result["files_staged"],3)
            self.assertTrue(result["secondary_clip_accepted"])
            self.assertEqual((sd/"switch/foj/rig/preview.fojrm").read_bytes(),
                             self.mesh)
            self.assertEqual((sd/"switch/foj/anims/preview.banim").read_bytes(),
                             self.first)
            self.assertEqual((sd/"switch/foj/anims/preview_b.banim").read_bytes(),
                             self.secondary)
            self.assertFalse(result["actual_original_ps3_asset_identity_verified"])

    def test_old_single_clip_mode_remains_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,_alt=self.assets(tmp)
            sd=Path(tmp)/"one-clip"
            result=prepare(sd,mesh,first)
            self.assertEqual(result["files_staged"],2)
            self.assertFalse(result["secondary_clip_accepted"])
            self.assertFalse((sd/"switch/foj/anims/preview_b.banim").exists())

    def test_private_prepare_refuses_overwrite_and_does_not_change_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,alt=self.assets(tmp)
            sd=Path(tmp)/"sd"
            before=[p.read_bytes() for p in (mesh,first,alt)]
            prepare(sd,mesh,first,alt)
            with self.assertRaises(ValueError):
                prepare(sd,mesh,first,alt)
            self.assertEqual([p.read_bytes() for p in (mesh,first,alt)],before)

    def test_private_prepare_rejects_duplicate_or_wrong_clip(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,alt=self.assets(tmp)
            with self.assertRaises(ValueError):
                prepare(Path(tmp)/"duplicate",mesh,first,first)
            raw=bytearray(self.secondary)
            struct.pack_into("<H",raw,11+5+66+1,0xffff)
            alt.write_bytes(raw)
            with self.assertRaises(ValueError):
                prepare(Path(tmp)/"mismatch",mesh,first,alt)
            self.assertFalse((Path(tmp)/"mismatch").exists())

    def test_private_prepare_cli_never_echoes_original_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,alt=self.assets(tmp)
            output=StringIO()
            with contextlib.redirect_stdout(output):
                result=prepare_main(
                    [str(mesh),str(first),"--secondary",str(alt),
                     "--output-root",str(Path(tmp)/"out")]
                )
            self.assertEqual(result,0)
            self.assertNotIn(tmp,output.getvalue())
            self.assertEqual(json.loads(output.getvalue())["files_staged"],3)
            alt.write_bytes(b"invalid animation")
            error=StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(prepare_main(
                    [str(mesh),str(first),"--secondary",str(alt),
                     "--output-root",str(Path(tmp)/"never-created")]),2)
            self.assertNotIn(tmp,error.getvalue())
            self.assertFalse((Path(tmp)/"never-created").exists())

    def run_host(self,sd,output,*,success=True):
        if not self.compiler:
            self.skipTest("Host cc not found")
        run=subprocess.run(
            [str(self.executable),str(sd),str(output)],
            cwd=ROOT,text=True,capture_output=True,timeout=30,
        )
        if success:
            self.assertEqual(run.returncode,0,run.stderr)
            return json.loads(run.stdout)
        self.assertNotEqual(run.returncode,0)
        self.assertNotIn(str(sd),run.stderr)
        self.assertNotIn(str(output),run.stderr)
        self.assertEqual(run.stdout,"")
        return run.stderr

    @staticmethod
    def ppm(path):
        raw=path.read_bytes()
        marker=b"P6\n480 320\n255\n"
        if not raw.startswith(marker) or len(raw)!=len(marker)+480*320*3:
            raise AssertionError("Native rendered frame must be 480x320 PPM")
        return raw[len(marker):]

    def test_native_real_production_parse_palette_and_wireframe(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,alt=self.assets(tmp)
            sd=Path(tmp)/"sd"
            prepare(sd,mesh,first,alt)
            output=Path(tmp)/"renders"
            output.mkdir()
            report=self.run_host(sd,output)
            self.assertEqual(report["frames_rendered"],9)
            self.assertTrue(report["secondary_clip_used"])
            self.assertEqual(report["rig_bone_count"],2)
            self.assertFalse(report["original_ps3_animation_verified"])
            names=("initial","play_025","paused","fade_0",
                   "fade_025","fade_050","fade_075","fade_done","reset")
            shots={name:self.ppm(output/(name+".ppm")) for name in names}
            self.assertEqual(shots["initial"],shots["fade_0"])
            self.assertEqual(shots["initial"],shots["reset"])
            self.assertEqual(shots["play_025"],shots["paused"])
            self.assertNotEqual(shots["initial"],shots["play_025"])
            self.assertNotEqual(shots["fade_025"],shots["fade_075"])
            self.assertNotEqual(shots["initial"],shots["fade_done"])
            # Each output captures real rasterized strokes, not blank frames.
            for name,pixels in shots.items():
                self.assertIn(bytes((218,228,189)),pixels,name)

    def test_native_host_missing_clip_fails_without_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,alt=self.assets(tmp)
            sd=Path(tmp)/"sd"
            prepare(sd,mesh,first,alt)
            (sd/"switch/foj/anims/preview.banim").unlink()
            destination=Path(tmp)/"evidence"
            destination.mkdir()
            self.run_host(sd,destination,success=False)
            self.assertEqual(list(destination.iterdir()),[])

    def test_native_host_incompatible_second_clip_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,alt=self.assets(tmp)
            sd=Path(tmp)/"sd"
            prepare(sd,mesh,first,alt)
            other=sd/"switch/foj/anims/preview_b.banim"
            raw=bytearray(other.read_bytes())
            struct.pack_into("<H",raw,11+5+66+1,0xffff)
            other.write_bytes(raw)
            destination=Path(tmp)/"evidence"
            destination.mkdir()
            self.run_host(sd,destination,success=False)
            self.assertEqual(list(destination.iterdir()),[])

    def test_native_output_does_not_overwrite_existing_private_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,alt=self.assets(tmp)
            sd=Path(tmp)/"sd"
            prepare(sd,mesh,first,alt)
            out=Path(tmp)/"renders"
            out.mkdir()
            original=b"owner-private-original"
            (out/"initial.ppm").write_bytes(original)
            self.run_host(sd,out,success=False)
            self.assertEqual((out/"initial.ppm").read_bytes(),original)

    def test_native_single_clip_executes_without_secondary_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh,first,_=self.assets(tmp)
            sd=Path(tmp)/"single"
            prepare(sd,mesh,first)
            out=Path(tmp)/"renders"
            out.mkdir()
            receipt=self.run_host(sd,out)
            self.assertFalse(receipt["secondary_clip_used"])
            self.assertEqual(len(list(out.glob("*.ppm"))),9)


if __name__=="__main__":
    unittest.main()
