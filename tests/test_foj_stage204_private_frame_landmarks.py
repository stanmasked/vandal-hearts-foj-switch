"""Stage 204 — generated-only proof that annotation points touch native PPM wire.

No original PS3 screenshots, images, models or human observations are used.
All images are in-memory invented wire crosses written to temporary files.
"""
from __future__ import annotations

import contextlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_foj_stage196_private_pose_observations import observation
from tools.foj_stage203_private_actor_evidence import HEADER,W,H
from tools.foj_stage204_private_frame_landmarks import (
    SCHEMA,REPORT_SCHEMA,STATE_ORDER,WIRE,
    RADIUS,inspect_landmarks,validate_bindings,main,read_bindings,
)

NAMES=("head","hand","hip","ankle","elbow")
SHAPE=((.26,.14),(.76,.27),(.58,.57),(.28,.82),(.76,.79))
LABELS=("initial","play_025","fade_025")


def landmarks_and_frames():
    obs=observation()
    for i,frame in enumerate(obs["frames"]):
        marks=[]
        for label,(x,y) in zip(NAMES,SHAPE):
            ex=x+.055*i
            ey=y+.01*i
            marks.append({
                "id":label,
                "ps3_xy":[.85*ex+.05,.8*ey+.05],
                "experimental_xy":[ex,ey],
            })
        frame["landmarks"]=marks[::-1] if i==1 else marks
        frame["ps3_time_seconds"]=i*.25
        frame["experimental_time_seconds"]=i*.25
    manifest={"schema":SCHEMA,"frame_labels":list(LABELS)}
    return obs,manifest


def draw_ppm(path,locations,*,mismatch=False):
    canvas=bytearray(W*H*3)
    for x,y in locations:
        px=int(round(x*(W-1)))
        py=int(round(y*(H-1)))
        if mismatch:
            px+=42
        for d in range(-3,4):
            for ax,ay in ((px+d,py),(px,py+d)):
                if 0<=ax<W and 0<=ay<H:
                    i=(ay*W+ax)*3
                    canvas[i:i+3]=WIRE
    path.write_bytes(HEADER+canvas)


def populate(folder:Path,obs,bindings):
    for i,label in enumerate(bindings["frame_labels"]):
        draw_ppm(
            folder/(label+".ppm"),
            [mark["experimental_xy"] for mark in obs["frames"][i]["landmarks"]],
        )


class Stage204FrameBindingTests(unittest.TestCase):
    def test_three_generated_frame_landmarks_are_supported(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,binding=landmarks_and_frames()
            populate(root,obs,binding)
            report=inspect_landmarks(obs,binding,root)
            self.assertEqual(report["schema"],REPORT_SCHEMA)
            self.assertTrue(report["research_landmarks_near_actual_native_ppm_wire"])
            self.assertEqual(report["stage203_named_frames_bound"],3)
            self.assertEqual(report["per_frame_max_research_wire_distance_pixels"],
                             [0.,0.,0.])
            self.assertFalse(report["original_ps3_capture_authenticated"])
            self.assertFalse(report["original_game_pose_accuracy_verified"])

    def test_research_points_must_refer_to_correct_named_frame(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,binding=landmarks_and_frames()
            populate(root,obs,binding)
            first=root/(LABELS[0]+".ppm")
            last=root/(LABELS[-1]+".ppm")
            first_bytes,last_bytes=first.read_bytes(),last.read_bytes()
            first.write_bytes(last_bytes)
            last.write_bytes(first_bytes)
            with self.assertRaises(ValueError):
                inspect_landmarks(obs,binding,root)

    def test_out_of_wire_landmark_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,binding=landmarks_and_frames()
            populate(root,obs,binding)
            obs["frames"][1]["landmarks"][0]["experimental_xy"]=[.08,.91]
            with self.assertRaises(ValueError):
                inspect_landmarks(obs,binding,root)

    def test_exact_radius_and_beyond(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,binding=landmarks_and_frames()
            populate(root,obs,binding)
            point=obs["frames"][0]["landmarks"][0]["experimental_xy"]
            point[0]+=4/(W-1)
            report=inspect_landmarks(obs,binding,root)
            self.assertGreater(report["per_frame_max_research_wire_distance_pixels"][0],0)
            point[0]+= (RADIUS+10)/(W-1)
            with self.assertRaises(ValueError):
                inspect_landmarks(obs,binding,root)

    def test_ppm_tampering_and_truncated_frame_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,binding=landmarks_and_frames()
            populate(root,obs,binding)
            frame=root/(LABELS[0]+".ppm")
            frame.write_bytes(b"invalid")
            with self.assertRaises(ValueError):
                inspect_landmarks(obs,binding,root)
            populate(root,obs,binding)
            raw=bytearray(frame.read_bytes())
            raw[:2]=b"P3"
            frame.write_bytes(raw)
            with self.assertRaises(ValueError):
                inspect_landmarks(obs,binding,root)

    def test_images_without_expected_wire_color_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,binding=landmarks_and_frames()
            populate(root,obs,binding)
            frame=root/(LABELS[1]+".ppm")
            data=frame.read_bytes().replace(WIRE,b"\xff\xff\xff")
            frame.write_bytes(data)
            with self.assertRaises(ValueError):
                inspect_landmarks(obs,binding,root)

    def test_symlink_frames_are_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,binding=landmarks_and_frames()
            populate(root,obs,binding)
            frame=root/(LABELS[1]+".ppm")
            renamed=root/"owner-unrelated.ppm"
            frame.rename(renamed)
            frame.symlink_to(renamed)
            with self.assertRaises(ValueError):
                inspect_landmarks(obs,binding,root)

    def test_invalid_label_duplicate_and_unsorted_manifest(self):
        obs,manifest=landmarks_and_frames()
        invalids=(
            ["initial","initial","fade_025"],
            ["fade_025","initial","play_025"],
            ["initial","play_025","../../private"],
            ["initial","play_025","not_an_actual_state"],
        )
        for labels in invalids:
            with self.subTest(labels=labels):
                bad={**manifest,"frame_labels":labels}
                with self.assertRaises(ValueError):
                    validate_bindings(bad,len(obs["frames"]))

    def test_manifest_must_cover_observation_count_exactly(self):
        obs,manifest=landmarks_and_frames()
        for labels in ([],["initial"],["initial","play_025"]):
            with self.subTest(labels=labels):
                with self.assertRaises(ValueError):
                    validate_bindings({**manifest,"frame_labels":labels},3)

    def test_manifest_unknown_fields_and_schema_version_rejected(self):
        obs,manifest=landmarks_and_frames()
        for bad in (
            {**manifest,"source_private_path":"/my/ps3/capture.png"},
            {**manifest,"schema":"invalid"},
            {**manifest,"frame_labels":"initial"},
        ):
            with self.assertRaises(ValueError):
                validate_bindings(bad,len(obs["frames"]))

    def test_annotation_id_and_collinearity_preconditions_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,manifest=landmarks_and_frames()
            populate(root,obs,manifest)
            obs["frames"][0]["landmarks"][0]["id"]=obs["frames"][0][
                "landmarks"][1]["id"]
            with self.assertRaises(ValueError):
                inspect_landmarks(obs,manifest,root)

    def test_unrecorded_operator_footage_never_becomes_authenticated(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,manifest=landmarks_and_frames()
            obs["ps3_observation"]["capture_recorded"]=False
            populate(root,obs,manifest)
            report=inspect_landmarks(obs,manifest,root)
            self.assertFalse(report["operator_declared_both_captures_recorded"])
            self.assertFalse(report["original_ps3_capture_authenticated"])
            self.assertFalse(report["original_actor_animation_binding_verified"])

    def test_missing_image_fails_without_partial_json_output(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,manifest=landmarks_and_frames()
            populate(root,obs,manifest)
            (root/(LABELS[-1]+".ppm")).unlink()
            with self.assertRaises(OSError):
                inspect_landmarks(obs,manifest,root)

    def test_cli_success_and_failure_never_echo_private_paths(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            obs,manifest=landmarks_and_frames()
            populate(root,obs,manifest)
            annotations=root/"confidential-PS3-landmarks.json"
            binding=root/"private-research-bindings.json"
            annotations.write_text(json.dumps(obs))
            binding.write_text(json.dumps(manifest))
            out=StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main([
                    "--observations",str(annotations),
                    "--bindings",str(binding),
                    "--frames-dir",str(root)]),0)
            report=json.loads(out.getvalue())
            self.assertEqual(report["schema"],REPORT_SCHEMA)
            self.assertNotIn(str(root),out.getvalue())
            self.assertNotIn("ps3_xy",out.getvalue())
            binding.write_text('{"schema":"a","schema":"b"}')
            err=StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main([
                    "--observations",str(annotations),
                    "--bindings",str(binding),
                    "--frames-dir",str(root)]),2)
            self.assertNotIn(str(root),err.getvalue())
            self.assertNotIn("confidential",err.getvalue())


if __name__=="__main__":
    unittest.main()
