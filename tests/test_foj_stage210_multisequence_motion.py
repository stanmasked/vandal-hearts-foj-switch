"""Stage210: generated-only multi-window articulated motion tests."""
from __future__ import annotations
import contextlib
import copy
from io import StringIO
import json
import math
from pathlib import Path
import tempfile
import unittest

from tests.test_foj_stage197_private_motion_lag import (
    fixture,pose,transformed,NAMES
)
from tools.foj_stage199_private_multiwindow import SCHEMA as INPUT_SCHEMA
from tools.foj_stage210_multisequence_motion import (
    SCHEMA,evaluate,main,normalized_sequence_fingerprint
)


def independent_motion(strength=0.,*,mirror=False,frames=12):
    doc=fixture(lag=0,mirror=mirror,frames=frames)
    if strength==0:
        return doc
    for i,row in enumerate(doc["frames"]):
        t=i*.15
        points=[list(pt) for pt in pose(t)]
        points[1][0]+=(strength*math.sin(t*2.6+.3))
        points[1][1]+=(strength*.7*math.cos(1.9*t+.1))
        source=transformed(points,camera_drift=.003*i)
        trial=transformed(points,mirror=mirror,camera_drift=-.006*i)
        row["landmarks"]=[
            {"id":name,"ps3_xy":list(source[j]),
             "experimental_xy":list(trial[j])}
            for j,name in enumerate(NAMES)
        ]
        if i%2:
            row["landmarks"].reverse()
    return doc


def payload(*,strengths=(0.,.05),
            independence="distinct_actions_operator_declared"):
    return {
        "schema":INPUT_SCHEMA,
        "motion_independence_declaration":independence,
        "observations":[
            independent_motion(s,mirror=bool(i%2))
            for i,s in enumerate(strengths)
        ]
    }


class Stage210PrivateMultisequenceTests(unittest.TestCase):
    def test_distinct_generated_motion_sequences_only_tentative(self):
        r=evaluate(payload())
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["windows_evaluated"],2)
        self.assertEqual(r["distinct_normalized_trajectories_detected"],2)
        self.assertFalse(r["duplicate_normalized_motion_detected"])
        self.assertEqual(
            r["diagnosis"],
            "tentative_operator_declared_multisequence_coherence_only"
        )
        self.assertTrue(r["operator_declared_distinct_actions"])
        self.assertFalse(r["motion_window_independence_authenticated"])
        self.assertFalse(r["original_ps3_animation_fidelity_verified"])

    def test_three_distinct_actions_have_informative_motion(self):
        r=evaluate(payload(strengths=(0.,.035,.07)))
        self.assertEqual(r["windows_evaluated"],3)
        self.assertEqual(r["windows_with_informative_motion"],3)
        self.assertEqual(r["coherent_2d_sequence_windows"],3)
        self.assertEqual(r["distinct_normalized_trajectories_detected"],3)
        self.assertEqual(r["unresolved_sequence_windows"],0)

    def test_mirrored_camera_cannot_create_independent_action(self):
        a=independent_motion(0.,mirror=False)
        b=independent_motion(0.,mirror=True)
        self.assertEqual(
            normalized_sequence_fingerprint(a),
            normalized_sequence_fingerprint(b)
        )
        doc=payload()
        doc["observations"]=[a,b]
        r=evaluate(doc)
        self.assertTrue(r["duplicate_normalized_motion_detected"])
        self.assertEqual(r["diagnosis"],
                         "duplicate_normalized_trajectory_not_independent")

    def test_reordered_landmark_lists_and_metadata_cannot_fake_new_action(self):
        first=independent_motion(.02)
        second=copy.deepcopy(first)
        for frame in second["frames"]:
            frame["landmarks"].reverse()
            frame["ps3_time_seconds"]+=.001
            frame["experimental_time_seconds"]+=.001
        doc=payload()
        doc["observations"]=[first,second]
        self.assertEqual(
            evaluate(doc)["diagnosis"],
            "duplicate_normalized_trajectory_not_independent"
        )

    def test_no_independence_declaration_stays_unverified(self):
        result=evaluate(payload(independence="not_established"))
        self.assertEqual(result["diagnosis"],"window_independence_not_established")
        self.assertFalse(result["operator_declared_distinct_actions"])

    def test_missing_capture_declaration_prevents_positive_result(self):
        doc=payload()
        doc["observations"][1]["ps3_observation"]["capture_recorded"]=False
        result=evaluate(doc)
        self.assertEqual(result["diagnosis"],"one_or_more_captures_not_declared")
        self.assertFalse(result["all_source_and_research_captures_operator_declared"])

    def test_single_bad_middle_frame_downgrades_all_window_consensus(self):
        doc=payload()
        row=doc["observations"][1]["frames"][5]["landmarks"]
        row[0]["ps3_xy"],row[1]["ps3_xy"]=row[1]["ps3_xy"],row[0]["ps3_xy"]
        result=evaluate(doc)
        self.assertEqual(
            result["diagnosis"],"unresolved_motion_difference_between_windows"
        )
        self.assertGreater(result["total_suspicious_motion_intervals"],0)

    def test_one_static_motion_sequence_is_not_motion_evidence(self):
        doc=payload()
        doc["observations"][1]=fixture(dynamic=False)
        result=evaluate(doc)
        self.assertEqual(result["diagnosis"],"unresolved_insufficient_motion_windows")
        self.assertLess(result["windows_with_informative_motion"],2)

    def test_clock_ratio_disagreement_prevents_multisequence_claim(self):
        doc=payload()
        sample=doc["observations"][1]
        sample["experimental_observation"]["timing_uncertainty_seconds"]=.04
        sample["ps3_observation"]["timing_uncertainty_seconds"]=.04
        for i,frame in enumerate(sample["frames"]):
            if i%2:
                frame["experimental_time_seconds"]+=.04
        result=evaluate(doc)
        self.assertEqual(result["diagnosis"],
                         "unresolved_window_timebase_disagreement")
        self.assertGreater(result["total_declared_clock_ratio_warnings"],0)

    def test_wrong_window_count_and_schema_are_rejected(self):
        for invalid in (
            {"observations":[]},
            {"observations":[independent_motion()]},
            {"observations":[independent_motion(i*.03)
                             for i in range(5)]},
            {"schema":"not-stage199"},
            {"motion_independence_declaration":"verified_by_program"},
            {"unrecognized_private_path":"/home/owner/ps3.mp4"},
        ):
            doc=payload()
            doc.update(invalid)
            with self.subTest(change=tuple(invalid)):
                with self.assertRaises(ValueError):
                    evaluate(doc)

    def test_wrong_landmark_names_and_clock_order_are_rejected(self):
        for wrong in ("id","timestamp"):
            doc=payload()
            frame=doc["observations"][1]["frames"][5]
            if wrong=="id":
                frame["landmarks"][0]["id"]="wrong_character_bone"
            else:
                frame["experimental_time_seconds"]=.1
            with self.subTest(wrong=wrong):
                with self.assertRaises(ValueError):
                    evaluate(doc)

    def test_input_manifest_not_mutated(self):
        doc=payload(strengths=(0.,.035,.07))
        copy_of=copy.deepcopy(doc)
        evaluate(doc)
        self.assertEqual(doc,copy_of)

    def test_report_leaves_game_media_raw_names_and_hashes_private(self):
        report=json.dumps(evaluate(payload()))
        for secret in ("ps3_xy","experimental_xy","left_hand",
                       "right_foot",".png",".fojrm",".pkg","sha256",
                       "/mnt/","/home/"):
            self.assertNotIn(secret,report.lower())
        self.assertFalse(json.loads(report)[
            "private_landmarks_and_source_hashes_exported"
        ])

    def test_cli_valid_and_bad_manifest_do_not_echo_paths(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"private-multiwindow-actor-capture.json"
            path.write_text(json.dumps(payload()))
            stdout=StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["--analyze",str(path)]),0)
            self.assertEqual(json.loads(stdout.getvalue())["schema"],SCHEMA)
            self.assertNotIn(td,stdout.getvalue())
            path.write_text('{"schema":"x","schema":"x"}')
            err=StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main(["--analyze",str(path)]),2)
            self.assertNotIn(td,err.getvalue())


if __name__=="__main__":
    unittest.main()
