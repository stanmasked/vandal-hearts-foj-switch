"""Stage 208: invented-only leave-one-out affine-versus-similarity evidence."""
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
from tools.foj_stage208_private_affine_crosscheck import (
    SCHEMA,MIN_POINTS,affine_parameters,compare,main,similarity_parameters
)
from tools.foj_stage203_private_actor_evidence import conduct
from tools.foj_stage201_generated_sd import generated_actors


def distorted(*, reflected=False):
    # The original-side shape is invented by a full 2D affine map
    # including unequal scaling and shear, while research annotations
    # retain the original invented motion and labels.
    doc=observation()
    for frame in doc["frames"]:
        for point in frame["landmarks"]:
            x,y=point["experimental_xy"]
            if reflected:
                x=1.-x
            x-=.5
            y-=.5
            point["ps3_xy"]=[
                .50+.88*x+.22*y,
                .47+.08*x+.41*y,
            ]
    return doc


class Stage208AffineCrossvalidationTests(unittest.TestCase):
    def test_ordinary_similarity_is_sufficient_for_invented_rotation(self):
        record=compare(observation())
        self.assertEqual(record["schema"],SCHEMA)
        self.assertEqual(record["diagnosis"],"two_d_similarity_sufficient")
        self.assertLess(record["median_similarity_holdout_rms"],.00001)
        self.assertLess(record["median_affine_holdout_rms"],.00001)
        self.assertAlmostEqual(
            record["median_affine_anisotropy_ratio"],1.,delta=.0001
        )
        self.assertFalse(record["original_ps3_camera_or_perspective_verified"])

    def test_affine_distortion_is_better_on_points_omitted_from_fit(self):
        record=compare(distorted())
        self.assertEqual(record["diagnosis"],
                         "tentative_affine_image_plane_nuisance")
        self.assertGreater(record["median_similarity_holdout_rms"],.05)
        self.assertLess(record["median_affine_holdout_rms"],.00001)
        self.assertGreater(record["median_affine_anisotropy_ratio"],1.3)
        self.assertEqual(record["affine_validation_improving_frames"],3)
        self.assertFalse(record["original_ps3_model_or_clip_verified"])

    def test_affine_fit_can_have_mirrored_determinant(self):
        record=compare(distorted(reflected=True))
        self.assertTrue(record["affine_orientation_sign_consistent"])
        self.assertLess(record["median_affine_holdout_rms"],.00001)
        self.assertFalse(record["automatic_anatomical_landmark_authentication"])

    def test_similarity_mirror_selection_uses_training_only(self):
        doc=observation(reflected=True)
        result=compare(doc)
        self.assertLess(result["median_similarity_holdout_rms"],.00001)
        self.assertEqual(result["diagnosis"],"two_d_similarity_sufficient")

    def test_source_time_not_inferred_from_pose_geometry(self):
        record=compare(fixture(lag=.15))
        self.assertEqual(record["frames_evaluated"],12)
        self.assertFalse(record["original_ps3_pose_or_timing_verified"])
        self.assertEqual(len(record["affine_holdout_rms_per_frame"]),12)

    def test_single_bad_landmark_not_silently_accepted_as_affine_camera(self):
        doc=observation()
        doc["frames"][1]["landmarks"][0]["ps3_xy"]=[.95,.95]
        result=compare(doc)
        self.assertNotEqual(
            result["diagnosis"],"tentative_affine_image_plane_nuisance"
        )
        self.assertGreater(result["high_holdout_mismatch_frames"],0)

    def test_unreported_capture_is_not_promoted_to_camera_discovery(self):
        doc=distorted()
        doc["ps3_observation"]["capture_recorded"]=False
        result=compare(doc)
        self.assertEqual(result["diagnosis"],"operator_capture_not_declared")
        self.assertFalse(result["source_capture_authenticated"])

    def test_four_point_crossvalidation_is_underdetermined(self):
        doc=observation()
        for frame in doc["frames"]:
            frame["landmarks"]=frame["landmarks"][:4]
        with self.assertRaises(ValueError):
            compare(doc)

    def test_collinear_source_geometry_is_invalid(self):
        with self.assertRaises(ValueError):
            affine_parameters(
                [(0.1+i*.1,.2) for i in range(5)],
                [(0.2+i*.1,.3) for i in range(5)]
            )

    def test_nearly_singular_affine_map_must_be_rejected(self):
        refs=[(.1,.1),(.8,.1),(.1,.8),(.8,.8),(.4,.6)]
        exps=[(.2,.2),(.8,.2),(.2,.8),(.8,.8),(.5,.6)]
        fit,ratio,sign=affine_parameters(refs,exps)
        self.assertAlmostEqual(ratio,1.,delta=.00001)
        self.assertEqual(sign,1)
        self.assertAlmostEqual(fit(exps[0])[0],refs[0][0],delta=1.e-9)
        with self.assertRaises(ValueError):
            affine_parameters(
                refs,[(.2+i*.1,.3+i*.001) for i in range(5)]
            )

    def test_disallows_mismatched_landmark_identity_and_clock(self):
        for invalid in ("identifier","duplicate_clock","nan"):
            doc=distorted()
            if invalid=="identifier":
                doc["frames"][2]["landmarks"][0]["id"]="other_joint"
            elif invalid=="duplicate_clock":
                doc["frames"][2]["ps3_time_seconds"]=.25
            else:
                doc["frames"][1]["landmarks"][0]["ps3_xy"][0]=float("nan")
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    compare(doc)

    def test_input_not_mutated(self):
        doc=distorted()
        pristine=copy.deepcopy(doc)
        compare(doc)
        self.assertEqual(doc,pristine)

    def test_report_omits_raw_names_and_private_asset_paths(self):
        report=json.dumps(compare(distorted()),sort_keys=True)
        for secret in (
            "ps3_xy","experimental_xy","ankle","right","/users/",
            ".banim",".fojrm","png_source","source_000"
        ):
            self.assertNotIn(secret,report.lower())
        self.assertFalse(json.loads(report)["manual_labels_or_coordinates_exported"])

    def test_cli_reports_status_without_echoing_private_file(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"operator-private-ps3-affine.json"
            path.write_text(json.dumps(distorted()))
            stdout=StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["--observations",str(path)]),0)
            self.assertEqual(json.loads(stdout.getvalue())["schema"],SCHEMA)
            self.assertNotIn(root,stdout.getvalue())
            path.write_text('{"invalid":1}')
            stderr=StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["--observations",str(path)]),2)
            self.assertNotIn(root,stderr.getvalue())

    def test_stage203_requires_both_bound_source_and_native_images(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            rig,a,b=generated_actors()
            assets=[root/name for name in
                    ("invented.fojrm","a.banim","b.banim")]
            for path,value in zip(assets,(rig,a,b),strict=True):
                path.write_bytes(value)
            destination=root/"should-not-exist"
            with self.assertRaises(ValueError):
                conduct(*assets,destination,affine_crosscheck=True)
            self.assertFalse(destination.exists())

    def test_native_c_source_png_and_research_wire_integrated_with_affine_audit(self):
        from tests.test_foj_stage205_private_source_png import fixtures
        from tools.foj_stage203_private_actor_evidence import HEADER,W,H
        from tools.foj_stage204_private_frame_landmarks import WIRE

        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            obs,binding,source,source_manifest=fixtures(root)
            rig,a,b=generated_actors()
            assets=[root/name for name in ("model.fojrm","a.banim","b.banim")]
            for p,data in zip(assets,(rig,a,b),strict=True):
                p.write_bytes(data)
            previous=root/"native-one"
            conduct(*assets,previous)
            for row,label in zip(obs["frames"],binding["frame_labels"]):
                picture=(previous/"private-frames"/(label+".ppm")).read_bytes()
                pixels=picture[len(HEADER):]
                candidates=[
                    (x,y) for y in range(H) for x in range(W)
                    if pixels[(y*W+x)*3:(y*W+x+1)*3]==WIRE
                ]
                self.assertGreater(len(candidates),20)
                selected=[candidates[0]]
                while len(selected)<5:
                    further=max(
                        candidates,key=lambda point:min(
                            (point[0]-other[0])**2+(point[1]-other[1])**2
                            for other in selected
                        )
                    )
                    self.assertNotIn(further,selected)
                    selected.append(further)
                for mark,(x,y) in zip(
                    sorted(row["landmarks"],key=lambda q:q["id"]),selected
                ):
                    mark["experimental_xy"]=[x/(W-1),y/(H-1)]
            obs_path=root/"operator-invented.json"
            manifest_path=root/"source-ids-private.json"
            binding_path=root/"wire-binding-private.json"
            obs_path.write_text(json.dumps(obs))
            manifest_path.write_text(json.dumps(source_manifest))
            binding_path.write_text(json.dumps(binding))
            final=root/"owner-private-evidence"
            result=conduct(
                *assets,final,observations=obs_path,
                source_png_dir=source,source_png_manifest=manifest_path,
                frame_bindings=binding_path,affine_crosscheck=True
            )
            self.assertTrue(result["private_affine_model_crosscheck_performed"])
            self.assertFalse(result["original_ps3_camera_verified_by_affine"])
            audit=json.loads(
                (final/"private-affine-crossvalidation.json").read_text()
            )
            self.assertEqual(audit["schema"],SCHEMA)
            self.assertFalse(audit["original_ps3_camera_or_perspective_verified"])


if __name__=="__main__":
    unittest.main()
