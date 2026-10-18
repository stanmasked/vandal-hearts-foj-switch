"""Stage 196: invented 2D landmark observations; no original PS3 frames.

The score is geometric evidence about *operator-supplied* correspondences,
not a photo/screenshot audit, original-engine recovery, or video verification.
"""
from __future__ import annotations

import contextlib
import copy
from io import StringIO
import json
import math
from pathlib import Path
import tempfile
import unittest

from tools.foj_stage196_private_pose_observations import (
    SCHEMA, REPORT_SCHEMA, MIN_FRAMES, MAX_FRAMES,
    align_observations, blank_template, fit, main, pairs_unique, private_read,
)

BASE=(
    (.22,.18),(.78,.23),(.64,.72),(.31,.79),(.53,.44)
)


def source_shape(frame):
    points=list(BASE)
    points[2]=(points[2][0]-.014*frame,points[2][1]+.022*frame)
    points[3]=(points[3][0]+.018*frame,points[3][1]-.012*frame)
    return points


def target(source, *, reflected=False):
    transformed=[]
    for x,y in source:
        if reflected:
            x=1-x
        cx,cy=x-.5,y-.5
        transformed.append((
            .48+.58*cx-.17*cy,
            .45+.17*cx+.58*cy,
        ))
    return transformed


def observation(*, reflected=False, shift=0.):
    data=blank_template()
    data["ps3_observation"]["capture_recorded"]=True
    data["experimental_observation"]["capture_recorded"]=True
    points_id=("left","right","shoulder","hip","ankle")
    for index in range(3):
        sample=source_shape(index)
        visible=target(sample,reflected=reflected)
        marks=[
            {"id":name,"ps3_xy":list(visible[i]),
             "experimental_xy":list(sample[i])}
            for i,name in enumerate(points_id)
        ]
        # Ordering of landmarks in the JSON can vary between frames.
        if index==1:
            marks.reverse()
        data["frames"].append({
            "ps3_time_seconds":.25*index,
            "experimental_time_seconds":.25*index+shift,
            "landmarks":marks,
        })
    return data


class Stage196ObservationComparatorTests(unittest.TestCase):
    def test_blank_never_claims_captured_frame(self):
        doc=blank_template()
        self.assertEqual(doc["schema"],SCHEMA)
        self.assertEqual(doc["frames"],[])
        self.assertFalse(doc["ps3_observation"]["capture_recorded"])
        self.assertFalse(doc["experimental_observation"]["capture_recorded"])
        with self.assertRaises(ValueError):
            align_observations(doc)

    def test_perfect_rotated_scaled_ordinary_fit_and_temporal_shape(self):
        report=align_observations(observation())
        self.assertEqual(report["schema"],REPORT_SCHEMA)
        self.assertEqual(report["number_of_frames"],3)
        self.assertEqual(report["landmarks_per_frame"],5)
        self.assertTrue(report["operator_declared_both_captures_recorded"])
        self.assertLess(report["ordinary_similarity_normalized_rms_median"],
                        .000001)
        self.assertLess(report["temporal_relative_shape_change_rms"],.000001)
        self.assertGreater(
            report["reflected_similarity_normalized_rms_median"],.1)
        self.assertFalse(report["ps3_bone_matrix_convention_verified"])
        self.assertFalse(report["original_ps3_capture_authenticity_verified"])

    def test_diagnostic_reflection_does_not_reinterpret_handedness(self):
        report=align_observations(observation(reflected=True))
        self.assertGreater(
            report["ordinary_similarity_normalized_rms_median"],.1)
        self.assertLess(
            report["reflected_similarity_normalized_rms_median"],.000001)
        self.assertFalse(report["automatic_handedness_selection"])

    def test_experimental_shape_mismatch_detected(self):
        changed=observation()
        changed["frames"][1]["landmarks"][0]["experimental_xy"][0]+=.11
        report=align_observations(changed)
        self.assertGreater(report["ordinary_similarity_normalized_rms_per_frame"][1],
                           .02)
        self.assertGreater(report["temporal_relative_shape_change_rms"],.01)

    def test_unrecorded_observations_do_not_turn_into_verified_capture(self):
        doc=observation()
        doc["ps3_observation"]["capture_recorded"]=False
        report=align_observations(doc)
        self.assertFalse(report["operator_declared_both_captures_recorded"])
        self.assertFalse(report["experiment_capture_authenticity_verified"])

    def test_reject_mismatched_frame_clocks(self):
        doc=observation(shift=.05)
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        doc["frames"][1]["experimental_time_seconds"]=0
        with self.assertRaises(ValueError):
            align_observations(doc)

    def test_reject_wrong_frame_order_or_same_frame_twice(self):
        doc=observation()
        doc["frames"][1],doc["frames"][2]=doc["frames"][2],doc["frames"][1]
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        doc["frames"][1]["ps3_time_seconds"]=0
        with self.assertRaises(ValueError):
            align_observations(doc)

    def test_reject_duplicate_or_changed_landmark_identifiers(self):
        doc=observation()
        doc["frames"][0]["landmarks"][0]["id"]="right"
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        doc["frames"][2]["landmarks"][0]["id"]="unknown"
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        doc["frames"][2]["landmarks"][0]["id"]="../confidential"
        with self.assertRaises(ValueError):
            align_observations(doc)

    def test_reject_nearly_collinear_and_duplicate_points(self):
        doc=observation()
        for i,p in enumerate(doc["frames"][0]["landmarks"]):
            p["ps3_xy"]=[.1+.12*i,.3]
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        for item in doc["frames"][0]["landmarks"]:
            item["experimental_xy"]=[.5,.5]
        with self.assertRaises(ValueError):
            align_observations(doc)

    def test_reject_boolean_nan_and_out_of_bounds_coordinates(self):
        for bad in (float("nan"),float("inf"),True,-.01,1.02,"0.5"):
            doc=observation()
            doc["frames"][0]["landmarks"][0]["ps3_xy"][0]=bad
            with self.subTest(str(bad)):
                with self.assertRaises(ValueError):
                    align_observations(doc)

    def test_frame_bounds_and_schema_fail_closed(self):
        doc=observation()
        doc["frames"]=doc["frames"][:MIN_FRAMES-1]
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        doc["frames"]+=[copy.deepcopy(doc["frames"][-1])
                        for _ in range(MAX_FRAMES)]
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        doc["schema"]="invalid"
        with self.assertRaises(ValueError):
            align_observations(doc)

    def test_unexpected_property_and_invalid_metadata_rejected(self):
        doc=observation()
        doc["private_path"]="/very/private/input.mp4"
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        doc["ps3_observation"]["source_kind"]="synthetic_test"
        with self.assertRaises(ValueError):
            align_observations(doc)
        doc=observation()
        doc["ps3_observation"]["capture_recorded"]="yes"
        with self.assertRaises(ValueError):
            align_observations(doc)

    def test_duplicate_json_keys_and_nan_literals_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"secret-observation.json"
            path.write_text('{"schema": "x", "schema": "y"}',encoding="utf-8")
            with self.assertRaises(ValueError):
                private_read(path)
            path.write_text('{"bad": NaN}',encoding="utf-8")
            with self.assertRaises(ValueError):
                private_read(path)

    def test_local_cli_init_is_blank_no_overwrite_and_never_leaks_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"very-private-original-game.json"
            output=StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--init",str(path)]),0)
            self.assertEqual(json.loads(path.read_text())["frames"],[])
            error=StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(main(["--init",str(path)]),2)
            self.assertNotIn(str(path),error.getvalue())
            self.assertNotIn("very-private",error.getvalue())

    def test_cli_valid_output_contains_no_identifiers_or_coordinates(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"protected-capture-observations.json"
            path.write_text(json.dumps(observation()),encoding="utf-8")
            output=StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--analyze",str(path)]),0)
            result=json.loads(output.getvalue())
            self.assertEqual(result["number_of_frames"],3)
            self.assertNotIn(str(path),output.getvalue())
            self.assertNotIn("left",output.getvalue())
            self.assertNotIn("ps3_xy",output.getvalue())
            self.assertNotIn("experimental_xy",output.getvalue())

    def test_cli_invalid_private_file_reports_no_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"confidential_ps3_screenshot.json"
            path.write_text('{"bogus": 1}',encoding="utf-8")
            error=StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(main(["--analyze",str(path)]),2)
            self.assertNotIn(folder,error.getvalue())
            self.assertNotIn("confidential",error.getvalue())


if __name__=="__main__":
    unittest.main()
