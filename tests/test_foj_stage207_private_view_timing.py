"""Stage 207 camera/pose/time diagnostics on entirely invented landmarks."""
from __future__ import annotations

import contextlib
import copy
from io import StringIO
import json
import math
from pathlib import Path
import tempfile
import unittest

from tests.test_foj_stage196_private_pose_observations import observation
from tests.test_foj_stage197_private_motion_lag import fixture
from tools.foj_stage207_private_view_timing import (
    SCHEMA,inspect,main,roll_span,transform_fit
)
from tools.foj_stage203_private_actor_evidence import conduct
from tools.foj_stage201_generated_sd import generated_actors


class Stage207ViewTiming(unittest.TestCase):
    def test_stable_original_pose_under_camera_similarity(self):
        report=inspect(observation())
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["diagnosis"],
                         "image_plane_similarity_stable_only")
        self.assertEqual(report["mirror_model_preference"],"unreflected")
        self.assertLess(report["selected_similarity_rms_median"],.00001)
        self.assertLess(report["max_image_plane_orientation_change_degrees"],.01)
        self.assertAlmostEqual(report["relative_apparent_size_span_ratio"],
                               1.,delta=.0001)
        self.assertFalse(report["gameplay_animation_fidelity_verified"])

    def test_correct_reflected_2d_case_keeps_reflection_as_hypothesis(self):
        report=inspect(observation(reflected=True))
        self.assertEqual(report["mirror_model_preference"],"reflected")
        self.assertLess(report["selected_similarity_rms_median"],1e-5)
        self.assertFalse(report["camera_yaw_pitch_or_3d_projection_verified"])

    def test_angles_near_180_are_close_not_full_circle(self):
        values=[math.radians(179),math.radians(-179),
                math.radians(178)]
        self.assertLess(roll_span(values),4.01)
        self.assertEqual(roll_span([0,0,0]),0)
        self.assertEqual(roll_span([math.pi]),0)

    def test_substantive_camera_roll_proxy_change_is_reported(self):
        payload=observation()
        row=payload["frames"][1]["landmarks"]
        center_x=sum(p["ps3_xy"][0] for p in row)/len(row)
        center_y=sum(p["ps3_xy"][1] for p in row)/len(row)
        angle=.39
        c,s=math.cos(angle),math.sin(angle)
        for item in row:
            x=item["ps3_xy"][0]-center_x
            y=item["ps3_xy"][1]-center_y
            item["ps3_xy"]=[
                center_x+c*x-s*y,
                center_y+s*x+c*y,
            ]
        r=inspect(payload)
        self.assertGreater(r["max_image_plane_orientation_change_degrees"],15)
        self.assertEqual(r["diagnosis"],
                         "possible_view_or_pose_inconsistency")
        self.assertFalse(r["camera_motion_independently_measured"])

    def test_differing_apparent_size_is_an_unresolved_nuisance(self):
        payload=observation()
        row=payload["frames"][1]["landmarks"]
        x=sum(p["ps3_xy"][0] for p in row)/len(row)
        y=sum(p["ps3_xy"][1] for p in row)/len(row)
        for item in row:
            a,b=item["ps3_xy"]
            item["ps3_xy"]=[x+1.5*(a-x),y+1.5*(b-y)]
        r=inspect(payload)
        self.assertGreater(r["relative_apparent_size_span_ratio"],1.3)
        self.assertEqual(r["diagnosis"],
                         "possible_view_or_pose_inconsistency")

    def test_bad_landmark_single_frame_has_worse_projection(self):
        payload=observation()
        payload["frames"][1]["landmarks"][0]["ps3_xy"]=[.95,.90]
        r=inspect(payload)
        self.assertGreater(r["selected_similarity_rms_worst"],.18)
        self.assertEqual(r["diagnosis"],
                         "possible_view_or_pose_inconsistency")

    def test_unreported_capture_cannot_claim_stable_provenance(self):
        payload=observation()
        payload["ps3_observation"]["capture_recorded"]=False
        result=inspect(payload)
        self.assertEqual(result["diagnosis"],"operator_capture_not_declared")
        self.assertFalse(result["source_ps3_capture_authenticated"])

    def test_three_frames_cannot_prove_timing_lag(self):
        r=inspect(observation())
        self.assertEqual(r["temporal_diagnostic"],
                         "insufficient_frames_for_lag_estimation")
        self.assertIsNone(r["temporal_candidate_offset_seconds"])
        self.assertFalse(r["original_animation_timing_verified"])

    def test_multi_frame_synthetic_motion_provides_only_tentative_lag(self):
        doc=fixture(lag=.15)
        r=inspect(doc)
        self.assertEqual(r["temporal_diagnostic"],"tentative_nonzero_shift")
        self.assertAlmostEqual(r["temporal_candidate_offset_seconds"],
                               .15,delta=.025)
        self.assertFalse(r["original_animation_timing_verified"])
        self.assertFalse(r["ps3_character_or_clip_identity_verified"])

    def test_static_motion_does_not_manufacture_temporal_estimate(self):
        doc=fixture(dynamic=False)
        r=inspect(doc)
        self.assertEqual(r["temporal_diagnostic"],
                         "not_resolvable_from_motion")
        self.assertIsNone(r["temporal_candidate_offset_seconds"])

    def test_invalid_correspondences_rejected_by_existing_schema(self):
        for change in ("wrong_name","collinear","wrong_time"):
            doc=observation()
            if change=="wrong_name":
                doc["frames"][2]["landmarks"][0]["id"]="alien_joint"
            elif change=="collinear":
                for i,mark in enumerate(doc["frames"][0]["landmarks"]):
                    mark["ps3_xy"]=[.1+.1*i,.2]
            else:
                doc["frames"][2]["ps3_time_seconds"]=.02
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    inspect(doc)

    def test_input_observations_are_never_mutated(self):
        document=observation()
        pristine=copy.deepcopy(document)
        inspect(document)
        self.assertEqual(document,pristine)

    def test_private_receipt_omits_raw_coordinates_and_names(self):
        report=json.dumps(inspect(observation()),sort_keys=True)
        for forbidden in ("ps3_xy","experimental_xy","ankle","shoulder",
                          ".pkg","/Users/","frame_000.png"):
            self.assertNotIn(forbidden,report)
        self.assertFalse(json.loads(report)["landmark_coordinates_included"])

    def test_cli_private_success_and_failure(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"operator-private-capture.json"
            path.write_text(json.dumps(observation()))
            stdout=StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["--observations",str(path)]),0)
            self.assertEqual(json.loads(stdout.getvalue())["schema"],SCHEMA)
            self.assertNotIn(td,stdout.getvalue())
            path.write_text('{"bad":true}')
            err=StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main(["--observations",str(path)]),2)
            self.assertNotIn(td,err.getvalue())

    def test_stage203_requires_both_verified_image_sides_for_view_audit(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            rig,a,b=generated_actors()
            assets=[folder/x for x in
                    ("model.fojrm","clip_a.banim","clip_b.banim")]
            for path,value in zip(assets,(rig,a,b),strict=True):
                path.write_bytes(value)
            output=folder/"must-not-exist"
            with self.assertRaises(ValueError):
                conduct(*assets,output,view_temporal_audit=True)
            self.assertFalse(output.exists())

    def test_full_generated_c_frames_and_source_pngs_enable_private_audit(self):
        from tests.test_foj_stage205_private_source_png import fixtures
        from tools.foj_stage203_private_actor_evidence import HEADER,W,H
        from tools.foj_stage204_private_frame_landmarks import WIRE
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            obs,binding,source,source_lock=fixtures(root)
            rig,a,b=generated_actors()
            assets=[root/n for n in ("rig.fojrm","clip_a.banim","clip_b.banim")]
            for path,raw in zip(assets,(rig,a,b),strict=True):
                path.write_bytes(raw)
            native=root/"first-native-pass"
            conduct(*assets,native)
            # Generated model pixels only, never game artwork. Associate
            # each operator mark with a distinct visible research wire.
            for row,label in zip(obs["frames"],binding["frame_labels"]):
                raw=(native/"private-frames"/(label+".ppm")).read_bytes()
                body=raw[len(HEADER):]
                candidates=[
                    (x,y) for y in range(H) for x in range(W)
                    if body[(y*W+x)*3:(y*W+x+1)*3]==WIRE
                ]
                self.assertGreater(len(candidates),20)
                chosen=[candidates[0]]
                while len(chosen)<5:
                    farthest=max(
                        candidates,key=lambda p:min(
                            (p[0]-q[0])**2+(p[1]-q[1])**2 for q in chosen
                        )
                    )
                    self.assertNotIn(farthest,chosen)
                    chosen.append(farthest)
                for mark,(x,y) in zip(
                    sorted(row["landmarks"],key=lambda v:v["id"]),chosen
                ):
                    mark["experimental_xy"]=[x/(W-1),y/(H-1)]
            annotations=root/"invented-observations.json"
            source_manifest=root/"invented-private-png-manifest.json"
            frame_binding=root/"invented-native-frame-binding.json"
            annotations.write_text(json.dumps(obs))
            source_manifest.write_text(json.dumps(source_lock))
            frame_binding.write_text(json.dumps(binding))
            final=root/"private-view-evidence"
            report=conduct(
                *assets,final,observations=annotations,
                source_png_dir=source,source_png_manifest=source_manifest,
                frame_bindings=frame_binding,view_temporal_audit=True
            )
            self.assertTrue(report["private_view_temporal_audit_performed"])
            self.assertTrue(report["source_png_captures_content_bound"])
            self.assertTrue(report["research_landmarks_bound_to_native_frames"])
            self.assertFalse(report["ps3_camera_or_animation_verified"])
            stored=json.loads(
                (final/"private-view-temporal-audit.json").read_text()
            )
            self.assertEqual(stored["schema"],SCHEMA)
            self.assertFalse(stored["gameplay_animation_fidelity_verified"])

    def test_cannot_create_provenance_from_metadata_missing_capture(self):
        doc=fixture(lag=0)
        doc["experimental_observation"]["capture_recorded"]=False
        report=inspect(doc)
        self.assertEqual(report["diagnosis"],"operator_capture_not_declared")


if __name__=="__main__":
    unittest.main()
