"""Stage203 strictly private end-to-end integration; invented-only fixtures."""
from __future__ import annotations

import contextlib
from io import StringIO
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest

from tests.test_decode_rig_banim import synthetic_banim,synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tests.test_foj_stage196_private_pose_observations import observation
from tests.test_foj_stage199_private_multiwindow import windows
from tools.export_local_rigmesh import pack_rig_mesh
from tools.foj_stage203_private_actor_evidence import (
    ROOT, SCHEMA, conduct, main, render_evidence, safe_destination,
)

class Stage203PrivateActorEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rig,_=pack_rig_mesh(
            synthetic_complete_model()[:-4]+synthetic_rig()
        )
        cls.primary=synthetic_banim()
        secondary=bytearray(cls.primary)
        struct.pack_into("<f",secondary,11+5+1+4+16,.25)
        cls.secondary=bytes(secondary)

    def assets(self,folder):
        paths=[Path(folder)/p for p in
               ("test-private.fojrm","test-motion-a.banim","test-motion-b.banim")]
        for path,data in zip(
            paths,(self.rig,self.primary,self.secondary),strict=True
        ):
            path.write_bytes(data)
        return paths

    def test_native_dual_clip_private_end_to_end_success(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            out=Path(td)/"evidence"
            report=conduct(rig,a,b,out)
            self.assertEqual(report["schema"],SCHEMA)
            self.assertTrue(report["private_host_render_succeeded"])
            self.assertTrue(report["secondary_clip_staged"])
            self.assertEqual(report["private_frames"],9)
            self.assertTrue(report["research_bind_identity_checked"])
            self.assertFalse(report["asset_identity_authenticated_as_original_ps3"])
            self.assertFalse(report["original_game_animation_accuracy_verified"])
            self.assertFalse(report["nexium_execution_tested_by_this_run"])
            self.assertEqual(len(list((out/"private-frames").glob("*.ppm"))),9)
            self.assertTrue((out/"private-pose-envelope.json").exists())
            self.assertTrue((out/"private-render-evidence.json").exists())
            self.assertEqual(
                json.loads((out/"private-evidence-status.json").read_text()),
                report,
            )
            analysis=json.loads((out/"private-render-evidence.json").read_text())
            self.assertTrue(analysis["pause_reset_zero_weight_consistent"])
            self.assertTrue(analysis["secondary_fade_motion_observed"])
            self.assertTrue(analysis["primary_pose_motion_observed"])

    def test_private_single_clip_supported_without_false_fade_claim(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            result=conduct(rig,a,None,Path(td)/"single")
            self.assertFalse(result["secondary_clip_staged"])
            self.assertFalse(result["secondary_motion_observed_in_private_frames"])
            self.assertFalse(result["original_game_animation_accuracy_verified"])

    def test_strict_output_permissions_and_preexisting_evidence_refused(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            out=Path(td)/"evidence"
            conduct(rig,a,b,out)
            self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o700)
            self.assertEqual(
                stat.S_IMODE(
                    (out/"private-pose-envelope.json").stat().st_mode
                ),0o600
            )
            with self.assertRaises(ValueError):
                conduct(rig,a,b,out)
            self.assertTrue((out/"private-evidence-status.json").exists())

    def test_incompatible_second_clip_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            bad=bytearray(b.read_bytes())
            struct.pack_into("<H",bad,11+5+66+1,0xffff)
            b.write_bytes(bad)
            out=Path(td)/"denied"
            with self.assertRaises(ValueError):
                conduct(rig,a,b,out)
            self.assertFalse(out.exists())

    def test_duplicate_animation_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            out=Path(td)/"denied"
            with self.assertRaises(ValueError):
                conduct(rig,a,a,out)
            self.assertFalse(out.exists())

    def test_symlink_output_does_not_overwrite_owner_content(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            owner=Path(td)/"owner"
            owner.mkdir()
            (owner/"keep.txt").write_text("do not touch")
            shadow=Path(td)/"shortcut"
            shadow.symlink_to(owner,target_is_directory=True)
            with self.assertRaises(ValueError):
                conduct(rig,a,b,shadow)
            self.assertEqual((owner/"keep.txt").read_text(),"do not touch")

    def test_public_repository_output_directory_forbidden(self):
        unsafe=ROOT/"docs"/"stage203_public_game_data"
        with self.assertRaises(ValueError):
            safe_destination(unsafe)
        # A newly created ignored local-data directory is permissible
        # only when its *parent* exists.
        if (ROOT/"local-data").is_dir():
            safe_destination(ROOT/"local-data"/"stage203_safely_ignored")

    def test_bad_private_observations_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            inp=Path(td)/"operator.json"
            inp.write_text('{"not_a_valid_annotation":1}')
            target=Path(td)/"not-created"
            with self.assertRaises(ValueError):
                conduct(rig,a,b,target,observations=inp)
            self.assertFalse(target.exists())

    def test_optional_ps3_annotation_is_not_authenticated(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            annotations=Path(td)/"unverified_observations.json"
            document=observation()
            document["ps3_observation"]["capture_recorded"]=False
            annotations.write_text(json.dumps(document))
            out=Path(td)/"private"
            result=conduct(rig,a,b,out,observations=annotations)
            self.assertTrue(result["operator_annotations_supplied"])
            self.assertFalse(result["operator_declared_both_captures_recorded"])
            self.assertFalse(result["actual_original_ps3_capture_authenticated"])
            self.assertFalse(
                result["annotations_proven_to_match_generated_frames"]
            )
            self.assertEqual(
                result["timing_diagnostic"],"requires_eight_or_more_frames"
            )
            self.assertTrue(
                (out/"private-operator-shape-comparison.json").exists()
            )

    def test_multiwindow_operator_declaration_not_verification(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            multi=Path(td)/"windows.json"
            multi.write_text(json.dumps(windows()))
            out=Path(td)/"bundle"
            result=conduct(rig,a,b,out,multiwindow=multi)
            self.assertTrue(result["independent_windows_submitted"])
            self.assertFalse(result["window_independence_authenticated"])
            self.assertTrue((out/"private-multiwindow-report.json").exists())
            self.assertFalse(result["original_game_animation_accuracy_verified"])

    def test_corrupt_private_ppm_cannot_pass_as_valid_render(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            out=Path(td)/"bundle"
            conduct(rig,a,b,out)
            frames=out/"private-frames"
            (frames/"reset.ppm").write_bytes(b"not a real picture")
            with self.assertRaises(ValueError):
                render_evidence(frames,secondary=True)

    def test_stdout_and_failure_never_expose_paths_or_source_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            rig,a,b=self.assets(td)
            output=StringIO()
            with contextlib.redirect_stdout(output):
                rc=main([
                    "--rig",str(rig),"--primary",str(a),
                    "--secondary",str(b),
                    "--output-root",str(Path(td)/"report")
                ])
            self.assertEqual(rc,0)
            text=output.getvalue()
            self.assertNotIn(td,text)
            self.assertNotIn("rms_source_vertex_displacement",text)
            self.assertNotIn("max_source_vertex_displacement",text)
            self.assertFalse(json.loads(text)[
                "original_game_animation_accuracy_verified"
            ])
            stderr=StringIO()
            with contextlib.redirect_stderr(stderr):
                rc=main([
                    "--rig",str(rig),"--primary",str(a),
                    "--output-root",str(Path(td)/"report")
                ])
            self.assertEqual(rc,2)
            self.assertNotIn(td,stderr.getvalue())
            self.assertNotIn("test-motion",stderr.getvalue())


if __name__=="__main__":
    unittest.main()
