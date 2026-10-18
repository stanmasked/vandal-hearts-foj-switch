"""Stage213: generated-only real-C adjustable camera projection tests.

No game-owned geometry, animation files or original PS3 captures.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

from tools.foj_stage201_generated_sd import generated_actors
from tools.foj_stage203_private_actor_evidence import (
    conduct,render_evidence,STATES,validated_camera,SCHEMA,main
)


class Stage213NativeCameraTests(unittest.TestCase):
    def create_assets(self,folder):
        rig,a,b=generated_actors()
        paths=[folder/x for x in ("private-rig.fojrm","a.banim","b.banim")]
        for path,data in zip(paths,(rig,a,b),strict=True):
            path.write_bytes(data)
        return paths

    def test_existing_default_research_camera_is_unchanged(self):
        self.assertEqual(validated_camera(.5,.2,1.),(.5,.2,1.))
        self.assertEqual(validated_camera(0,0,2),(0.,0.,2.))

    def test_camera_rejects_nan_inf_bool_strings_and_extreme_angles(self):
        invalid=(
            (float("nan"),.2,1.),
            (.5,float("inf"),1.),
            (True,.2,1.),
            ("0.5",.2,1.),
            (.5,.2,False),
            (4.0,.2,1.),
            (.5,-2.0,1.),
            (.5,.2,0.0),
            (.5,.2,3.5),
        )
        for camera in invalid:
            with self.subTest(camera=camera):
                with self.assertRaises(ValueError):
                    validated_camera(*camera)

    def test_invalid_camera_rejected_before_private_output_creation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.create_assets(root)
            out=root/"no-partial-output"
            with self.assertRaises(ValueError):
                conduct(rig,a,b,out,camera_yaw=float("nan"))
            self.assertFalse(out.exists())
            with self.assertRaises(ValueError):
                conduct(rig,a,b,out,camera_zoom=0.05)
            self.assertFalse(out.exists())

    def test_custom_native_camera_changes_actual_nine_c_frames(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.create_assets(root)
            baseline=root/"native-default"
            adjusted=root/"native-new-view"
            before=conduct(rig,a,b,baseline)
            after=conduct(
                rig,a,b,adjusted,camera_yaw=-.65,
                camera_pitch=.4,camera_zoom=.86
            )
            self.assertFalse(before["research_camera_customized"])
            self.assertTrue(after["research_camera_customized"])
            self.assertFalse(after["source_game_camera_match_verified"])
            self.assertTrue(after["private_host_render_succeeded"])
            self.assertEqual(after["private_frames"],9)
            self.assertNotEqual(
                (baseline/"private-frames"/"initial.ppm").read_bytes(),
                (adjusted/"private-frames"/"initial.ppm").read_bytes()
            )
            for name in STATES:
                self.assertTrue((adjusted/"private-frames"/(name+".ppm")).exists())
            native=render_evidence(adjusted/"private-frames",secondary=True)
            self.assertTrue(native["pause_reset_zero_weight_consistent"])
            self.assertTrue(native["primary_pose_motion_observed"])

    def test_camera_receipt_is_private_and_never_claims_ps3_projection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.create_assets(root)
            output=root/"camera-bundle"
            result=conduct(rig,a,b,output,camera_yaw=-.7,
                           camera_pitch=.1,camera_zoom=1.2)
            path=output/"private-research-camera.json"
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            record=json.loads(path.read_text())
            self.assertEqual(
                record["schema"],
                "foj.stage213.private_research_projection.v1"
            )
            self.assertAlmostEqual(record["yaw_radians"],-.7)
            self.assertAlmostEqual(record["pitch_radians"],.1)
            self.assertAlmostEqual(record["zoom_factor"],1.2)
            self.assertFalse(record["original_ps3_camera_authenticated"])
            self.assertFalse(record["source_game_view_equivalence_verified"])
            self.assertNotIn(str(root),json.dumps(result))

    def test_original_legacy_native_C_invocation_remains_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.create_assets(root)
            out=root/"default"
            conduct(rig,a,b,out)
            binary=out/"private-actor-host-smoke"
            sd=out/"private-switch-sd"
            legacy=root/"two-argument-native"
            legacy.mkdir()
            proc=subprocess.run(
                [str(binary),str(sd),str(legacy)],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                timeout=15,check=False,
            )
            self.assertEqual(proc.returncode,0,proc.stderr[:200])
            self.assertEqual(
                (legacy/"initial.ppm").read_bytes(),
                (out/"private-frames"/"initial.ppm").read_bytes()
            )

    def test_native_C_rejects_non_numeric_camera_without_writing_frames(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.create_assets(root)
            out=root/"compiled"
            conduct(rig,a,b,out)
            binary=out/"private-actor-host-smoke"
            sd=out/"private-switch-sd"
            for k,args in enumerate((
                ["nan",".2","1"],[".5","inf","1"],
                ["0junk",".2","1"],["4",".2","1"],
                [".5",".2","0"],[".5",".2","20"],
            )):
                folder=root/f"rejected-{k}"
                folder.mkdir()
                p=subprocess.run(
                    [str(binary),str(sd),str(folder),*args],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    timeout=10,check=False,
                )
                self.assertNotEqual(p.returncode,0)
                self.assertEqual(list(folder.iterdir()),[])

    def test_cli_reports_success_without_leaking_local_projection_values(self):
        from io import StringIO
        import contextlib
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.create_assets(root)
            out=root/"cli-native"
            stdout=StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main([
                    "--rig",str(rig),"--primary",str(a),
                    "--secondary",str(b),"--output-root",str(out),
                    "--camera-yaw","-.67","--camera-pitch",".31",
                    "--camera-zoom",".98",
                ]),0)
            receipt=json.loads(stdout.getvalue())
            self.assertEqual(receipt["frames_generated"],9)
            self.assertFalse(receipt["original_game_animation_accuracy_verified"])
            self.assertNotIn(d,stdout.getvalue())
            self.assertNotIn("-.67",stdout.getvalue())


if __name__=="__main__":
    unittest.main()
