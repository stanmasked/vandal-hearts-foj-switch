"""Stage 199: generated-only independent-window consensus / alias safeguards."""
from __future__ import annotations

import contextlib
import copy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_foj_stage197_private_motion_lag import fixture
from tests.test_foj_stage198_motion_ambiguity import repeating_fixture
from tools.foj_stage199_private_multiwindow import (
    SCHEMA, REPORT_SCHEMA, evaluate, main, template
)


def windows(*, offsets=(.15,.15), mirror_second=True,
            declaration="distinct_actions_operator_declared"):
    frames=[]
    for i,shift in enumerate(offsets):
        frames.append(fixture(lag=shift,mirror=mirror_second and i%2==1))
    # Third+ session gets same invented movement with a separately
    # ordered set of landmarks. This is strictly synthetic and DOES NOT
    # establish independence of genuine source-game actions.
    for i in range(2,len(frames)):
        for f in frames[i]["frames"]:
            f["landmarks"].reverse()
    return {
        "schema":SCHEMA,
        "motion_independence_declaration":declaration,
        "observations":frames,
    }


class Stage199MultiwindowTests(unittest.TestCase):
    def test_two_agreeing_shift_windows_are_tentative_only(self):
        report=evaluate(windows())
        self.assertEqual(report["schema"],REPORT_SCHEMA)
        self.assertEqual(report["diagnosis"],"tentative_common_shift")
        self.assertAlmostEqual(report["offset_seconds"],.15,delta=.025)
        self.assertEqual(report["window_count"],2)
        self.assertEqual(report["leave_one_window_out_instability_count"],0)
        self.assertEqual(report["locally_ambiguous_window_count"],0)
        self.assertTrue(report["holdout_improved_over_zero"])
        self.assertFalse(report["original_game_timing_verified"])
        self.assertFalse(report["original_ps3_capture_authenticated"])

    def test_three_windows_agree_and_each_one_can_be_held_out(self):
        result=evaluate(windows(offsets=(.15,.15,.15)))
        self.assertEqual(result["window_count"],3)
        self.assertEqual(result["leave_one_window_out_instability_count"],0)
        self.assertEqual(result["diagnosis"],"tentative_common_shift")

    def test_negative_offset_has_correct_sign(self):
        report=evaluate(windows(offsets=(-.1,-.1)))
        self.assertAlmostEqual(report["offset_seconds"],-.1,delta=.025)
        self.assertEqual(report["diagnosis"],"tentative_common_shift")

    def test_two_zero_lag_motions_are_not_a_nonzero_discovery(self):
        report=evaluate(windows(offsets=(0.,0.)))
        self.assertEqual(report["diagnosis"],"no_clear_common_shift")
        self.assertLessEqual(abs(report["offset_seconds"]),.025)

    def test_conflicting_window_lags_are_never_called_consensus(self):
        report=evaluate(windows(offsets=(.15,-.1)))
        self.assertTrue(report["disagreeing_window_offsets"])
        self.assertNotEqual(report["diagnosis"],"tentative_common_shift")

    def test_cyclic_motion_alias_cannot_be_promoted(self):
        first=repeating_fixture()
        second=copy.deepcopy(first)
        for f in second["frames"]:
            f["landmarks"].reverse()
        payload=windows()
        payload["observations"]=[first,second]
        result=evaluate(payload)
        self.assertNotEqual(result["diagnosis"],"tentative_common_shift")
        self.assertGreater(result["locally_ambiguous_window_count"],0)

    def test_single_corrupted_window_downgrades_consensus(self):
        payload=windows()
        payload["observations"][1]["frames"][4]["landmarks"][0][
            "experimental_xy"]=[.94,.07]
        report=evaluate(payload)
        self.assertNotEqual(report["diagnosis"],"tentative_common_shift")
        self.assertGreater(report["locally_ambiguous_window_count"],0)

    def test_no_independence_declaration_means_ambiguous(self):
        report=evaluate(windows(declaration="not_established"))
        self.assertFalse(report["operator_declared_distinct_actions"])
        self.assertEqual(report["diagnosis"],"ambiguous_multiwindow")

    def test_unrecorded_capture_must_never_promote_result(self):
        payload=windows()
        payload["observations"][0]["ps3_observation"]["capture_recorded"]=False
        report=evaluate(payload)
        self.assertFalse(report["all_capture_recordings_operator_declared"])
        self.assertNotEqual(report["diagnosis"],"tentative_common_shift")

    def test_reject_duplicate_window_payloads(self):
        item=fixture()
        with self.assertRaises(ValueError):
            evaluate({
                "schema":SCHEMA,
                "motion_independence_declaration":
                    "distinct_actions_operator_declared",
                "observations":[item,copy.deepcopy(item)]
            })

    def test_reject_invalid_independent_window_timeline(self):
        payload=windows()
        payload["observations"][1]["frames"][5]["ps3_time_seconds"]=.30
        with self.assertRaises(ValueError):
            evaluate(payload)

    def test_blank_template_has_no_valid_observations(self):
        payload=template()
        self.assertEqual(payload["schema"],SCHEMA)
        self.assertEqual(payload["motion_independence_declaration"],
                         "not_established")
        self.assertEqual(len(payload["observations"]),2)
        for row in payload["observations"]:
            self.assertEqual(row["frames"],[])
            self.assertFalse(row["ps3_observation"]["capture_recorded"])
        with self.assertRaises(ValueError):
            evaluate(payload)

    def test_window_and_metadata_bounds(self):
        for invalid in (
            {"motion_independence_declaration":"malicious_unknown"},
            {"schema":"not-stage199"},
            {"observations":[]},
            {"observations":[fixture()]},
            {"observations":[fixture() for _ in range(5)]},
        ):
            value=windows()
            value.update(invalid)
            with self.subTest(invalid=list(invalid)):
                with self.assertRaises(ValueError):
                    evaluate(value)

    def test_invalid_search_grid_is_rejected(self):
        for kwargs in (
            {"max_shift":1.},
            {"step":float("nan")},
            {"step":0},
            {"max_shift":.19,"step":.025}
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    evaluate(windows(),**kwargs)

    def test_input_remains_unchanged(self):
        value=windows()
        before=copy.deepcopy(value)
        evaluate(value)
        self.assertEqual(value,before)

    def test_report_excludes_raw_landmarks_and_source_identifiers(self):
        report=evaluate(windows())
        text=json.dumps(report,sort_keys=True)
        for forbidden in (
            "ps3_xy","experimental_xy","head","left_hand",
            "right_foot","/private/","original_game_capture.mp4"
        ):
            self.assertNotIn(forbidden,text.lower())
        self.assertFalse(report["original_landmarks_and_media_included"])

    def test_cli_init_analyze_and_path_privacy(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"confidential-ps3-multiwindow.json"
            with contextlib.redirect_stdout(StringIO()):
                self.assertEqual(main(["--init",str(path)]),0)
            self.assertEqual(json.loads(path.read_text())["observations"][0][
                "frames"],[])
            error=StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(main(["--init",str(path)]),2)
            self.assertNotIn(folder,error.getvalue())
            path.write_text(json.dumps(windows()),encoding="utf-8")
            out=StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["--analyze",str(path)]),0)
            self.assertEqual(json.loads(out.getvalue())["diagnosis"],
                             "tentative_common_shift")
            self.assertNotIn(folder,out.getvalue())
            path.write_text('{"schema":"x","schema":"y"}',encoding="utf-8")
            error=StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(main(["--analyze",str(path)]),2)
            self.assertNotIn(folder,error.getvalue())
            self.assertNotIn("confidential",error.getvalue())


if __name__=="__main__":
    unittest.main()
