"""Stage209: wholly invented time-indexed 2D landmarks and native C fixtures."""
from __future__ import annotations

import contextlib
import copy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_foj_stage197_private_motion_lag import fixture, transformed, pose, NAMES
from tools.foj_stage209_private_motion_coherence import (
    SCHEMA, inspect, main
)
from tools.foj_stage201_generated_sd import generated_actors
from tools.foj_stage203_private_actor_evidence import conduct


class Stage209InterframeTests(unittest.TestCase):
    def test_matching_generated_articulated_sequence_has_coherent_changes(self):
        result=inspect(fixture(lag=0))
        self.assertEqual(result["schema"],SCHEMA)
        self.assertEqual(result["frames_evaluated"],12)
        self.assertEqual(result["interframe_intervals"],11)
        self.assertEqual(result["landmarks_per_frame"],6)
        self.assertEqual(result["diagnosis"],"shape_transition_consistent_only")
        self.assertGreaterEqual(result["informative_motion_intervals"],2)
        self.assertEqual(result["suspect_motion_intervals"],0)
        self.assertFalse(result["gameplay_motion_fidelity_verified"])

    def test_camera_inplane_similarity_drift_not_reported_as_wrong_pose(self):
        doc=fixture(lag=0)
        # Per-frame uniform scaling/translation/rotation is already
        # present in the invented source and experimental observations.
        r=inspect(doc)
        self.assertLess(r["largest_interframe_shape_difference_rms"],.005)
        self.assertFalse(r["camera_perspective_recovered"])

    def test_wrong_middle_frame_affects_two_neighbor_intervals(self):
        doc=fixture(lag=0)
        marks=doc["frames"][5]["landmarks"]
        # Keep IDs and chronology valid while exchanging two visible
        # source limb locations in exactly one middle frame.
        marks[0]["ps3_xy"],marks[1]["ps3_xy"]=(
            marks[1]["ps3_xy"],marks[0]["ps3_xy"]
        )
        report=inspect(doc)
        self.assertGreaterEqual(report["suspect_motion_intervals"],2)
        self.assertGreaterEqual(report["adjacent_suspect_interval_pairs"],1)
        self.assertEqual(
            report["diagnosis"],
            "unresolved_local_motion_or_annotation_mismatch"
        )

    def test_motion_seen_only_in_original_source_is_not_validated(self):
        doc=fixture(dynamic=False)
        source=doc["frames"][5]["landmarks"]
        source[0]["ps3_xy"]=[.12,.12]
        record=inspect(doc)
        self.assertGreater(record["one_stream_static_other_moving_intervals"],0)
        self.assertGreater(record["suspect_motion_intervals"],0)
        self.assertFalse(record["original_character_or_clip_authenticated"])

    def test_static_sequence_does_not_create_positive_motion_evidence(self):
        result=inspect(fixture(dynamic=False))
        self.assertEqual(
            result["diagnosis"],
            "unresolved_insufficient_articulated_motion"
        )
        self.assertEqual(result["informative_motion_intervals"],0)
        self.assertEqual(result["suspect_motion_intervals"],0)

    def test_operator_declared_timing_disagreement_is_separate(self):
        doc=fixture(lag=0)
        doc["ps3_observation"]["timing_uncertainty_seconds"]=.04
        doc["experimental_observation"]["timing_uncertainty_seconds"]=.04
        for i,frame in enumerate(doc["frames"]):
            if i%2:
                frame["experimental_time_seconds"]+=.04
        r=inspect(doc)
        self.assertGreater(r["interval_clock_ratio_above_tolerance_count"],0)
        self.assertEqual(
            r["diagnosis"],"unresolved_interval_timebase_disagreement"
        )
        self.assertFalse(r["original_ps3_frame_clock_verified"])

    def test_not_recorded_is_never_declared_coherent_evidence(self):
        doc=fixture(lag=0)
        doc["ps3_observation"]["capture_recorded"]=False
        result=inspect(doc)
        self.assertEqual(result["diagnosis"],"operator_capture_not_declared")
        self.assertFalse(result["source_capture_hardware_authenticated"])

    def test_nonzero_generated_offset_is_only_a_suspicious_sequence(self):
        lagged=inspect(fixture(lag=.15))
        matched=inspect(fixture(lag=0))
        self.assertGreater(
            lagged["median_interframe_shape_difference_rms"],
            matched["median_interframe_shape_difference_rms"]
        )
        self.assertFalse(lagged["original_ps3_frame_clock_verified"])

    def test_repeated_motion_cannot_authenticate_absolute_phase(self):
        doc=fixture(lag=0)
        for i,row in enumerate(doc["frames"]):
            original=transformed(pose((i%3)*.25))
            trial=transformed(pose((i%3)*.25),camera_drift=.01)
            row["landmarks"]=[
                {"id":name,"ps3_xy":list(original[j]),
                 "experimental_xy":list(trial[j])}
                for j,name in enumerate(NAMES)
            ]
        r=inspect(doc)
        self.assertEqual(r["diagnosis"],"shape_transition_consistent_only")
        self.assertFalse(r["original_ps3_frame_clock_verified"])
        self.assertFalse(r["gameplay_motion_fidelity_verified"])

    def test_invalid_identifier_and_reversed_clocks_are_rejected(self):
        for corrupt in ("id","timestamp","nan"):
            doc=fixture(lag=0)
            if corrupt=="id":
                doc["frames"][2]["landmarks"][0]["id"]="wrong_id"
            elif corrupt=="timestamp":
                doc["frames"][4]["experimental_time_seconds"]=.1
            else:
                doc["frames"][1]["landmarks"][0]["ps3_xy"][0]=float("nan")
            with self.subTest(corrupt=corrupt):
                with self.assertRaises(ValueError):
                    inspect(doc)

    def test_input_document_not_modified(self):
        doc=fixture(lag=0)
        untouched=copy.deepcopy(doc)
        inspect(doc)
        self.assertEqual(doc,untouched)

    def test_private_summary_never_outputs_coordinates_names_or_file_paths(self):
        raw=json.dumps(inspect(fixture(lag=0)))
        for secret in ("ps3_xy","experimental_xy","left_hand",
                       ".png",".fojrm",".pkg","/home/"):
            self.assertNotIn(secret,raw)
        self.assertFalse(
            json.loads(raw)["original_landmark_names_or_positions_published"]
        )

    def test_private_cli_success_and_corrupt_input_error_without_path(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"private-ps3-pose-data.json"
            path.write_text(json.dumps(fixture(lag=0)))
            stdout=StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["--observations",str(path)]),0)
            self.assertEqual(json.loads(stdout.getvalue())["schema"],SCHEMA)
            self.assertNotIn(td,stdout.getvalue())
            path.write_text('{"invalid":"private owner file"}')
            stderr=StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["--observations",str(path)]),2)
            self.assertNotIn(td,stderr.getvalue())

    def test_stage203_requires_two_bound_image_sides(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            rig,a,b=generated_actors()
            assets=[root/x for x in ("model.fojrm","a.banim","b.banim")]
            for p,blob in zip(assets,(rig,a,b),strict=True):
                p.write_bytes(blob)
            out=root/"no-evidence-created"
            with self.assertRaises(ValueError):
                conduct(*assets,out,interframe_coherence=True)
            self.assertFalse(out.exists())

    def test_actual_native_generated_C_frames_and_source_PNG_are_bound(self):
        from tests.test_foj_stage205_private_source_png import fixtures
        from tools.foj_stage203_private_actor_evidence import HEADER,W,H
        from tools.foj_stage204_private_frame_landmarks import WIRE
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            obs,binding,source,manifest=fixtures(root)
            rig,a,b=generated_actors()
            assets=[root/x for x in ("model.fojrm","a.banim","b.banim")]
            for p,blob in zip(assets,(rig,a,b),strict=True):
                p.write_bytes(blob)
            previous=root/"generated-C-model"
            conduct(*assets,previous)
            for row,label in zip(obs["frames"],binding["frame_labels"]):
                image=(previous/"private-frames"/(label+".ppm")).read_bytes()
                frame=image[len(HEADER):]
                choices=[
                    (x,y) for y in range(H) for x in range(W)
                    if frame[3*(y*W+x):3*(y*W+x+1)]==WIRE
                ]
                self.assertGreater(len(choices),20)
                selected=[choices[0]]
                while len(selected)<5:
                    far=max(
                        choices,key=lambda point:min(
                            (point[0]-q[0])**2+(point[1]-q[1])**2
                            for q in selected
                        )
                    )
                    self.assertNotIn(far,selected)
                    selected.append(far)
                for mark,(x,y) in zip(
                    sorted(row["landmarks"],key=lambda v:v["id"]),selected
                ):
                    mark["experimental_xy"]=[x/(W-1),y/(H-1)]
            obs_file=root/"synthetic-operator-observations.json"
            bind_file=root/"generated-frame-binding.json"
            manifest_file=root/"generated-source-manifest.json"
            obs_file.write_text(json.dumps(obs))
            bind_file.write_text(json.dumps(binding))
            manifest_file.write_text(json.dumps(manifest))
            final=root/"private-interframe-evidence"
            evidence=conduct(
                *assets,final,observations=obs_file,source_png_dir=source,
                source_png_manifest=manifest_file,frame_bindings=bind_file,
                interframe_coherence=True
            )
            self.assertTrue(
                evidence["private_interframe_motion_coherence_performed"]
            )
            self.assertFalse(
                evidence["original_ps3_motion_verified_by_interframe"]
            )
            sub=json.loads(
                (final/"private-interframe-coherence.json").read_text()
            )
            self.assertEqual(sub["schema"],SCHEMA)
            self.assertFalse(sub["gameplay_motion_fidelity_verified"])


if __name__=="__main__":
    unittest.main()
