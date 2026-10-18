"""Stage 197 synthetic-only temporal lag checks; no original PS3 frames."""
from __future__ import annotations

import contextlib
import copy
from io import StringIO
import json
import math
from pathlib import Path
import tempfile
import unittest

from tools.foj_stage196_private_pose_observations import blank_template
from tools.foj_stage197_private_motion_lag import compare, main, SCHEMA

NAMES=("head","left_hand","right_hand","hip","left_foot","right_foot")


def pose(t):
    # Nonperiodic across the short interval, with independently swinging
    # limbs: translation/scale/rotation alone cannot explain the change.
    return (
        (.50+.03*math.sin(2.7*t),.18+.02*math.cos(3.3*t)),
        (.24+.12*math.sin(3.2*t+.2),.40+.09*math.cos(2.4*t)),
        (.75-.10*math.sin(3.7*t+.1),.35+.07*math.sin(2.8*t)),
        (.47+.02*math.sin(1.3*t),.63+.01*math.cos(2.1*t)),
        (.34+.13*math.sin(4.4*t+.4),.88-.05*math.cos(2.9*t)),
        (.67-.09*math.sin(3.9*t),.86+.06*math.cos(3.4*t)),
    )


def transformed(points, *, mirror=False, camera_drift=0.):
    # Intentional nuisance pose translation, per-frame uniform scale,
    # in-plane rotation and optional reflection. The lag comparator must
    # derive signals from internal articulated motion instead.
    angle=.32+camera_drift
    scale=.76
    c,s=math.cos(angle),math.sin(angle)
    result=[]
    for x,y in points:
        if mirror:
            x=1.-x
        x,y=x-.5,y-.5
        result.append((.53+scale*(c*x-s*y),
                       .47+scale*(s*x+c*y)))
    return result


def fixture(*, lag=.15, mirror=False, dynamic=True, frames=12):
    data=blank_template()
    for field in ("ps3_observation","experimental_observation"):
        data[field]["capture_recorded"]=True
        data[field]["timing_uncertainty_seconds"]=.01
    for i in range(frames):
        t=round(i*.15,8)
        original=pose(t) if dynamic else pose(0)
        trial=pose(t-lag) if dynamic else pose(0)
        original=transformed(original,camera_drift=.003*i)
        trial=transformed(trial,mirror=mirror,camera_drift=-.006*i)
        marks=[
            {"id":name,
             "ps3_xy":list(original[j]),
             "experimental_xy":list(trial[j])}
            for j,name in enumerate(NAMES)
        ]
        if i%2:
            marks.reverse()
        data["frames"].append({
            "ps3_time_seconds":t,
            "experimental_time_seconds":t,
            "landmarks":marks,
        })
    return data


class Stage197PrivateTimingTests(unittest.TestCase):
    def test_correct_positive_lag_across_camera_nuisance(self):
        report=compare(fixture(lag=.15))
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["samples_total"],12)
        self.assertGreaterEqual(report["common_interior_samples"],5)
        self.assertAlmostEqual(
            report["best_candidate_offset_seconds"],.15,delta=.025)
        self.assertEqual(report["diagnosis"],"tentative_nonzero_shift")
        self.assertTrue(report["holdout_improved_over_zero_offset"])
        self.assertFalse(report["original_ps3_capture_authenticated"])

    def test_negative_lag_has_opposite_sign(self):
        report=compare(fixture(lag=-.1))
        self.assertAlmostEqual(report["best_candidate_offset_seconds"],
                               -.1,delta=.025)
        self.assertEqual(report["diagnosis"],"tentative_nonzero_shift")

    def test_zero_lag_is_not_falsely_declared_delayed(self):
        report=compare(fixture(lag=0))
        self.assertLessEqual(
            abs(report["best_candidate_offset_seconds"]),.025)
        self.assertEqual(report["diagnosis"],"no_clear_shift")

    def test_mirrored_or_rotated_camera_preserves_shape_lag(self):
        mirrored=compare(fixture(lag=.15,mirror=True))
        ordinary=compare(fixture(lag=.15))
        self.assertEqual(mirrored["best_candidate_offset_seconds"],
                         ordinary["best_candidate_offset_seconds"])
        self.assertFalse(mirrored["original_bone_convention_verified"])

    def test_static_pose_cannot_generate_fake_timing_evidence(self):
        with self.assertRaises(ValueError):
            compare(fixture(dynamic=False))

    def test_insufficient_common_window_rejected(self):
        with self.assertRaises(ValueError):
            compare(fixture(frames=8),max_shift=.2)
        with self.assertRaises(ValueError):
            compare(fixture(frames=8),max_shift=.30,step=.025)

    def test_no_matching_ids_between_frames_rejected(self):
        data=fixture()
        data["frames"][2]["landmarks"][0]["id"]="other_point"
        with self.assertRaises(ValueError):
            compare(data)

    def test_unsorted_or_duplicate_timestamps_rejected(self):
        for corrupt in ("duplicate","reverse"):
            doc=fixture()
            if corrupt=="duplicate":
                doc["frames"][4]["experimental_time_seconds"]=.45
            else:
                doc["frames"][4],doc["frames"][3]=(
                    doc["frames"][3],doc["frames"][4])
            with self.subTest(corrupt=corrupt):
                with self.assertRaises(ValueError):
                    compare(doc)

    def test_invalid_precision_and_bad_frame_type_rejected(self):
        doc=fixture()
        doc["ps3_observation"]["timing_uncertainty_seconds"]=.5
        with self.assertRaises(ValueError):
            compare(doc)
        doc=fixture()
        doc["frames"][0]["landmarks"][0]["experimental_xy"][0]=float("nan")
        with self.assertRaises(ValueError):
            compare(doc)

    def test_unreported_capture_must_not_receive_tentative_status(self):
        document=fixture(lag=.15)
        document["ps3_observation"]["capture_recorded"]=False
        result=compare(document)
        self.assertFalse(result["both_capture_recordings_operator_declared"])
        self.assertEqual(result["diagnosis"],"ambiguous")
        self.assertFalse(result["original_ps3_capture_authenticated"])

    def test_uncertainty_downgrades_tentative_to_ambiguous(self):
        doc=fixture(lag=.15)
        doc["ps3_observation"]["timing_uncertainty_seconds"]=.08
        doc["experimental_observation"]["timing_uncertainty_seconds"]=.08
        result=compare(doc)
        self.assertFalse(result["declared_uncertainty_allows_step_resolution"])
        self.assertEqual(result["diagnosis"],"ambiguous")

    def test_search_boundary_must_not_claim_precise_lag(self):
        report=compare(fixture(lag=.2))
        self.assertTrue(report["search_edge_reached"])
        self.assertNotEqual(report["diagnosis"],"tentative_nonzero_shift")

    def test_wrong_shift_grid_and_nonfinite_args_rejected(self):
        for kw in (
            {"max_shift":.19,"step":.025},
            {"max_shift":1.0},
            {"step":0},
            {"step":float("nan")},
            {"max_shift":True},
            {"max_shift":.3,"step":.005},
        ):
            with self.subTest(kw=kw):
                with self.assertRaises(ValueError):
                    compare(fixture(),**kw)

    def test_report_contains_no_points_or_original_file_names(self):
        data=fixture()
        report=compare(data)
        message=json.dumps(report,sort_keys=True)
        for forbidden in (
            "ps3_xy","experimental_xy","left_hand","right_foot",
            "banim","bmodel","original_capture.mp4","/users/",
        ):
            self.assertNotIn(forbidden,message.lower())
        self.assertFalse(report["raw_landmarks_and_source_images_in_report"])
        self.assertFalse(report["original_animation_pacing_verified"])

    def test_blank_template_fails_without_inventing_observations(self):
        with self.assertRaises(ValueError):
            compare(blank_template())

    def test_cli_genuine_synthetic_fixture_and_private_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"very-private-movement-observations.json"
            path.write_text(json.dumps(fixture(lag=.15)),encoding="utf-8")
            output=StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--analyze",str(path)]),0)
            report=json.loads(output.getvalue())
            self.assertEqual(report["diagnosis"],"tentative_nonzero_shift")
            self.assertNotIn(temp,output.getvalue())
            path.write_text('{"not_an_observation":42}',encoding="utf-8")
            error=StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(main(["--analyze",str(path)]),2)
            self.assertNotIn(temp,error.getvalue())
            self.assertNotIn("very-private",error.getvalue())


if __name__=="__main__":
    unittest.main()
