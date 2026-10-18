"""Stage212: invented-only unified source PNG / PPM / 2D motion tests."""
from __future__ import annotations

import contextlib
import copy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_foj_stage205_private_source_png import png
from tests.test_foj_stage204_private_frame_landmarks import draw_ppm
from tests.test_foj_stage210_multisequence_motion import independent_motion
from tests.test_foj_stage197_private_motion_lag import fixture
from tools.foj_stage204_private_frame_landmarks import SCHEMA as FRAME_SCHEMA
from tools.foj_stage204_private_frame_landmarks import STATE_ORDER
from tools.foj_stage205_private_source_png import prepare
from tools.foj_stage199_private_multiwindow import SCHEMA as WINDOW_SCHEMA
from tools.foj_stage211_private_multisequence_image_binding import (
    SCHEMA as BINDING_SCHEMA
)
from tools.foj_stage212_private_joint_evidence import SCHEMA,main,review


def prepared(root,*,replay_png=False,replay_motion=False,static=False):
    root=Path(root)
    observations={
        "schema":WINDOW_SCHEMA,
        "motion_independence_declaration":"distinct_actions_operator_declared",
        "observations":[],
    }
    config={"schema":BINDING_SCHEMA,"windows":[]}
    for k in range(2):
        place=root/f"private-window-{k}"
        place.mkdir()
        data=(fixture(dynamic=False,frames=8) if static and k==1 else
              independent_motion(
                  0.0 if replay_motion else k*.07,
                  mirror=bool(k%2),frames=8
              ))
        names=list(STATE_ORDER[:8])
        source_dir=place/"original-side-png"
        source_dir.mkdir()
        frame_dir=place/"research-native-ppm"
        frame_dir.mkdir()
        frame_binding={"schema":FRAME_SCHEMA,"frame_labels":names}
        for i,(row,label) in enumerate(zip(data["frames"],names)):
            seed=15+i*13+(0 if replay_png else k*67)
            (source_dir/f"frame_{i:03d}.png").write_bytes(
                png(seed=seed,color=6 if i%2 else 2)
            )
            # Draw a synthetic cross at each of the actual operator-
            # marked experimental coordinates: this only tests that
            # Stage211 binds pixels to their supposed research frame.
            draw_ppm(
                frame_dir/(label+".ppm"),
                [item["experimental_xy"] for item in row["landmarks"]]
            )
        source_manifest=place/"source-manifest-PRIVATE.json"
        native_binding=place/"native-binding-PRIVATE.json"
        source_manifest.write_text(json.dumps(prepare(data,source_dir)))
        native_binding.write_text(json.dumps(frame_binding))
        config["windows"].append({
            "source_png_dir":str(source_dir),
            "source_manifest":str(source_manifest),
            "research_frames_dir":str(frame_dir),
            "research_binding":str(native_binding),
        })
        observations["observations"].append(data)
    return observations,config


class Stage212UnifiedEvidenceTests(unittest.TestCase):
    def test_two_distinct_moving_windows_still_not_original_ps3_proof(self):
        with tempfile.TemporaryDirectory() as t:
            observations,bindings=prepared(t)
            r=review(observations,bindings)
            self.assertEqual(r["schema"],SCHEMA)
            self.assertEqual(r["windows_evaluated"],2)
            self.assertEqual(r["source_png_frames_bound"],16)
            self.assertTrue(r["two_sided_image_binding_passed"])
            self.assertTrue(r["per_window_articulated_motion_coherence_passed"])
            self.assertEqual(
                r["diagnosis"],
                "tentative_joint_local_2d_consistency_only"
            )
            self.assertFalse(r["original_ps3_gameplay_authenticated"])
            self.assertFalse(r["true_window_independence_authenticated"])
            self.assertFalse(
                r["original_ps3_skeletal_animation_fidelity_verified"]
            )

    def test_repeated_source_frames_veto_motion_consistency(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t,replay_png=True)
            r=review(obs,config)
            self.assertTrue(r["cross_window_source_png_reuse_detected"])
            self.assertEqual(r["diagnosis"],
                             "duplicate_or_invalid_image_window_evidence")
            self.assertFalse(r["two_sided_image_binding_passed"])

    def test_same_motion_different_source_pngs_is_not_independent(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t,replay_motion=True)
            r=review(obs,config)
            self.assertFalse(r["cross_window_source_png_reuse_detected"])
            self.assertTrue(r["normalized_motion_replay_detected"])
            self.assertEqual(r["diagnosis"],
                             "duplicate_normalized_motion_windows")

    def test_static_window_cannot_count_as_motion_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t,static=True)
            r=review(obs,config)
            self.assertFalse(r["per_window_articulated_motion_coherence_passed"])
            self.assertEqual(r["diagnosis"],
                             "unresolved_sequence_geometry_or_timebase")

    def test_missing_action_declaration_blocks_approval(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            obs["motion_independence_declaration"]="not_established"
            result=review(obs,config)
            self.assertEqual(result["diagnosis"],
                             "missing_operator_recording_or_action_declaration")
            self.assertFalse(
                result["all_operator_capture_and_action_declarations_present"]
            )

    def test_missing_source_capture_declaration_blocks_approval(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            obs["observations"][0]["ps3_observation"]["capture_recorded"]=False
            r=review(obs,config)
            self.assertEqual(r["diagnosis"],
                             "missing_operator_recording_or_action_declaration")

    def test_corrupted_local_source_png_invalidates_both_checks(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            folder=Path(config["windows"][1]["source_png_dir"])
            (folder/"frame_005.png").write_bytes(b"not PNG")
            with self.assertRaises(ValueError):
                review(obs,config)

    def test_wrong_research_landmark_position_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            obs["observations"][1]["frames"][3]["landmarks"][0][
                "experimental_xy"
            ]=[.01,.99]
            with self.assertRaises(ValueError):
                review(obs,config)

    def test_atomic_joint_audit_rejects_updated_png_and_manifest_midrun(self):
        from unittest.mock import patch
        from tools.foj_stage205_private_source_png import prepare
        from tools.foj_stage212_private_joint_evidence import (
            motion_audit as genuine_motion
        )
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            folder=Path(config["windows"][0]["source_png_dir"])
            manifest=Path(config["windows"][0]["source_manifest"])

            def changed_after_motion(document):
                result=genuine_motion(document)
                # Both the PNG and the *valid* matching manifest are
                # replaced between audits. The Stage211 summaries are
                # identical, but raw-content witnesses must differ.
                (folder/"frame_000.png").write_bytes(png(seed=207))
                manifest.write_text(
                    json.dumps(prepare(document["observations"][0],folder))
                )
                return result

            with patch(
                "tools.foj_stage212_private_joint_evidence.motion_audit",
                side_effect=changed_after_motion
            ):
                with self.assertRaises(ValueError):
                    review(obs,config)

    def test_joint_audit_rejects_changed_wire_pixels_despite_same_labels(self):
        from unittest.mock import patch
        from tools.foj_stage212_private_joint_evidence import (
            motion_audit as genuine_motion
        )
        from tools.foj_stage203_private_actor_evidence import HEADER
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            directory=Path(config["windows"][1]["research_frames_dir"])
            frame=directory/"initial.ppm"

            def changed_after_motion(document):
                result=genuine_motion(document)
                raw=bytearray(frame.read_bytes())
                # First image row, far away from the operator's pose:
                # this affects exact evidence identity but NOT wire
                # proximity or native PPM layout.
                raw[len(HEADER)+9]=(raw[len(HEADER)+9]+1)%256
                frame.write_bytes(raw)
                return result

            with patch(
                "tools.foj_stage212_private_joint_evidence.motion_audit",
                side_effect=changed_after_motion
            ):
                with self.assertRaises(ValueError):
                    review(obs,config)

    def test_unchanged_operator_inputs_not_mutated(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            original=copy.deepcopy(obs)
            before=copy.deepcopy(config)
            review(obs,config)
            self.assertEqual(obs,original)
            self.assertEqual(config,before)

    def test_no_asset_paths_coordinates_or_hashes_in_report(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            result=json.dumps(review(obs,config))
            for forbidden in (
                t,"sha256","frame_000","ps3_xy","experimental_xy",
                ".fojrm",".banim",".pkg","research-native-ppm",
                "head","left_hand"
            ):
                self.assertNotIn(forbidden,result)
            self.assertFalse(json.loads(result)[
                "raw_images_coordinates_hashes_or_private_paths_exported"
            ])

    def test_cli_success_and_failure_are_path_free(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,config=prepared(t)
            observations=root/"operator-motion-private.json"
            bindings=root/"source-and-research-private.json"
            observations.write_text(json.dumps(obs))
            bindings.write_text(json.dumps(config))
            out=StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["--observations",str(observations),
                                       "--bindings",str(bindings)]),0)
            self.assertEqual(json.loads(out.getvalue())["schema"],SCHEMA)
            self.assertNotIn(t,out.getvalue())
            bindings.write_text('{"schema":"invalid"}')
            err=StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main(["--observations",str(observations),
                                       "--bindings",str(bindings)]),2)
            self.assertNotIn(t,err.getvalue())

    def test_bad_observation_structure_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            obs,config=prepared(t)
            obs["observations"][1]["frames"][0]["landmarks"][0]["id"]="alien"
            with self.assertRaises(ValueError):
                review(obs,config)


if __name__=="__main__":
    unittest.main()
