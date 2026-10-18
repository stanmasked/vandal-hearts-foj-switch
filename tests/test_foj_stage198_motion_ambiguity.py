"""Stage 198: entirely synthetic lag-alias and annotation sensitivity tests."""
from __future__ import annotations

import contextlib
import copy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_foj_stage197_private_motion_lag import fixture, pose
from tools.foj_stage198_motion_ambiguity import inspect, main, SCHEMA
from tools.foj_stage197_private_motion_lag import compare
from tools.foj_stage196_private_pose_observations import blank_template


def repeating_fixture():
    # An invented 0.30-second two-pose movement sampled every 0.15s.
    # Ordinary and offset-by-one-cycle shift predictions are identical.
    result=fixture(lag=.15)
    shapes=(pose(0),pose(.45))
    for i,frame in enumerate(result["frames"]):
        for j,point in enumerate(frame["landmarks"]):
            name=point["id"]
            index=("head","left_hand","right_hand","hip",
                   "left_foot","right_foot").index(name)
            point["ps3_xy"]=list(shapes[i%2][index])
            point["experimental_xy"]=list(shapes[(i+1)%2][index])
    return result


class Stage198MotionAmbiguityTests(unittest.TestCase):
    def test_clean_motion_keeps_previous_tentative_verdict(self):
        report=inspect(fixture(lag=.15))
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["source_diagnostic_schema"],
                         "foj.stage197.private_motion_timing_lag.v1")
        self.assertEqual(report["original_stage197_verdict"],
                         "tentative_nonzero_shift")
        self.assertEqual(report["robustness_adjusted_verdict"],
                         "tentative_nonzero_shift")
        self.assertEqual(report["jackknife_landmarks_checked"],6)
        self.assertEqual(report["jackknife_lag_changes_count"],0)
        self.assertEqual(report["suspicious_frame_count"],0)
        self.assertEqual(report["distinct_plausible_shift_count"],0)

    def test_negative_motion_and_mirror_do_not_introduce_false_alias(self):
        negative=inspect(fixture(lag=-.1,mirror=True))
        self.assertAlmostEqual(negative["estimated_offset_seconds"],
                               -.1,delta=.025)
        self.assertFalse(negative["possible_repeating_motion_alias"])
        self.assertEqual(negative["jackknife_lag_changes_count"],0)

    def test_zero_offset_remains_clear_when_motion_is_nonperiodic(self):
        result=inspect(fixture(lag=0))
        self.assertEqual(result["original_stage197_verdict"],
                         "no_clear_shift")
        self.assertEqual(result["robustness_adjusted_verdict"],
                         "no_clear_shift")

    def test_repeating_motion_has_distinct_equally_good_lags(self):
        result=inspect(repeating_fixture())
        self.assertTrue(result["possible_repeating_motion_alias"])
        self.assertGreater(result["distinct_plausible_shift_count"],0)
        self.assertNotEqual(result["robustness_adjusted_verdict"],
                            "tentative_nonzero_shift")
        self.assertFalse(result["original_game_timing_verified"])

    def test_wrong_point_in_single_frame_is_flagged_not_auto_corrected(self):
        data=fixture(lag=.15)
        point=data["frames"][4]["landmarks"][0]
        point["experimental_xy"]=[.94,.07]
        result=inspect(data)
        self.assertGreater(result["suspicious_frame_count"],0)
        self.assertTrue(result["possible_annotation_or_camera_disagreement"])
        self.assertNotEqual(result["robustness_adjusted_verdict"],
                            "tentative_nonzero_shift")

    def test_only_four_landmarks_cannot_claim_redundancy(self):
        data=fixture()
        for row in data["frames"]:
            row["landmarks"]=[p for p in row["landmarks"]
                              if p["id"] not in ("left_foot","right_foot")]
        result=inspect(data)
        self.assertFalse(result["sufficient_landmark_redundancy"])
        self.assertEqual(result["jackknife_landmarks_checked"],0)
        self.assertNotEqual(result["robustness_adjusted_verdict"],
                            "tentative_nonzero_shift")

    def test_unreported_original_capture_cannot_be_promoted(self):
        data=fixture()
        data["ps3_observation"]["capture_recorded"]=False
        result=inspect(data)
        self.assertFalse(result["both_capture_recordings_operator_declared"])
        self.assertNotEqual(result["robustness_adjusted_verdict"],
                            "tentative_nonzero_shift")
        self.assertFalse(result["original_ps3_capture_authenticated"])

    def test_no_source_mutation_when_comparing(self):
        data=fixture()
        pristine=copy.deepcopy(data)
        inspect(data)
        self.assertEqual(data,pristine)

    def test_reject_invalid_and_changed_landmark_identifiers(self):
        data=fixture()
        data["frames"][4]["landmarks"][0]["id"]="swapped_name"
        with self.assertRaises(ValueError):
            inspect(data)

    def test_reject_static_motion_and_blank_template(self):
        with self.assertRaises(ValueError):
            inspect(fixture(dynamic=False))
        with self.assertRaises(ValueError):
            inspect(blank_template())

    def test_invalid_candidate_grid_fails_closed(self):
        for settings in (
            {"max_shift":1.2}, {"step":float("nan")},
            {"max_shift":True}, {"max_shift":.19,"step":.025}
        ):
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    inspect(fixture(),**settings)

    def test_aggregate_output_never_contains_annotations_or_paths(self):
        payload=json.dumps(inspect(fixture()),sort_keys=True)
        for forbidden in ("ps3_xy","experimental_xy","left_hand",
                          "right_foot","/private/","original_capture.mp4"):
            self.assertNotIn(forbidden,payload.lower())
        self.assertFalse(json.loads(payload)["raw_source_landmarks_included"])

    def test_cli_valid_and_invalid_cases_are_private(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"confidential_source_ps3.json"
            path.write_text(json.dumps(fixture()),encoding="utf-8")
            output=StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--analyze",str(path)]),0)
            result=json.loads(output.getvalue())
            self.assertEqual(result["schema"],SCHEMA)
            self.assertNotIn(str(path),output.getvalue())
            path.write_text('{"invalid":"source"}',encoding="utf-8")
            stderr=StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["--analyze",str(path)]),2)
            self.assertNotIn(str(path),stderr.getvalue())
            self.assertNotIn("confidential",stderr.getvalue())


if __name__=="__main__":
    unittest.main()
