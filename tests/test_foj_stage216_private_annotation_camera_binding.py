"""Stage216 synthetic-only end-to-end native camera + annotation binding.

No original PS3 images, models, clips or user paths are in this test.
"""
from __future__ import annotations

import contextlib
from io import StringIO
import json
from pathlib import Path
import stat
import tempfile
import unittest

from tests.test_foj_stage204_private_frame_landmarks import (
    landmarks_and_frames, WIRE
)
from tests.test_foj_stage205_private_source_png import png
from tools.foj_stage201_generated_sd import generated_actors
from tools.foj_stage203_private_actor_evidence import conduct, HEADER, W, H
from tools.foj_stage205_private_source_png import prepare
from tools.foj_stage214_private_multicamera_preview import preview
from tools.foj_stage215_private_camera_choice_lock import lock_choice
from tools.foj_stage216_private_annotation_camera_binding import (
    SCHEMA, REPORT, receipt, check, main
)


class Stage216AnnotationCameraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        rig, a, b = generated_actors()
        cls.assets = tuple(cls.root / n for n in (
            "private-rig.fojrm", "private-a.banim", "private-b.banim"
        ))
        for path, data in zip(cls.assets, (rig, a, b), strict=True):
            path.write_bytes(data)
        cls.previews = cls.root / "camera-research"
        preview(*cls.assets, cls.previews,
                [".5,.2,1", "-.65,.4,.86"])
        cls.lock = cls.root / "PRIVATE-camera.json"
        lock_choice(cls.previews, 1, cls.lock)
        cls.final = cls.root / "final-native"
        conduct(*cls.assets, cls.final,
                camera_yaw=-.65, camera_pitch=.4, camera_zoom=.86)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.local = tempfile.TemporaryDirectory(dir=self.root)
        root = Path(self.local.name)
        obs, labels = landmarks_and_frames()
        for row, label in zip(obs["frames"], labels["frame_labels"],
                              strict=True):
            raw = (self.final / "private-frames" / (label + ".ppm")
                  ).read_bytes()[len(HEADER):]
            wire_pixels = [
                (x, y) for y in range(H) for x in range(W)
                if raw[(y*W+x)*3:(y*W+x+1)*3] == WIRE
            ]
            self.assertGreater(len(wire_pixels), 20)
            selected = [wire_pixels[0]]
            while len(selected) < 5:
                chosen = max(
                    wire_pixels, key=lambda p: min(
                        (p[0]-q[0])**2 + (p[1]-q[1])**2
                        for q in selected
                    )
                )
                selected.append(chosen)
            for marker, (x, y) in zip(
                sorted(row["landmarks"], key=lambda m: m["id"]),
                selected, strict=True
            ):
                marker["experimental_xy"] = [x/(W-1), y/(H-1)]
                marker["ps3_xy"] = [x/(W-1), y/(H-1)]

        self.capture_dir = root / "synthetic-pngs"
        self.capture_dir.mkdir()
        for i in range(len(obs["frames"])):
            (self.capture_dir / f"frame_{i:03d}.png").write_bytes(
                png(seed=13+17*i)
            )
        manifest = prepare(obs, self.capture_dir)
        self.observations = root / "PRIVATE-annotations.json"
        self.frame_bindings = root / "PRIVATE-frame-labels.json"
        self.source_manifest = root / "PRIVATE-source-manifest.json"
        for path, data in (
            (self.observations, obs),
            (self.frame_bindings, labels),
            (self.source_manifest, manifest),
        ):
            path.write_text(json.dumps(data), encoding="utf-8")
        self.output = root / "PRIVATE-camera-annotation-binding.json"
        self.args = (
            self.previews, self.lock, self.final, self.observations,
            self.frame_bindings, self.source_manifest, self.capture_dir,
            self.output
        )

    def tearDown(self):
        self.local.cleanup()

    def test_generated_native_renderer_end_to_end_success(self):
        result = receipt(*self.args)
        self.assertEqual(result["schema"], REPORT)
        self.assertEqual(result["locally_bound_frame_count"], 3)
        self.assertTrue(result["annotation_camera_binding_locked_privately"])
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)
        hidden = json.loads(self.output.read_text())
        self.assertEqual(hidden["schema"], SCHEMA)
        self.assertEqual(len(hidden["camera_lock_sha256_private"]), 64)
        self.assertFalse(hidden["original_ps3_capture_authenticated"])
        verified = check(*self.args)
        self.assertTrue(verified["annotation_camera_binding_reverified"])
        self.assertFalse(verified["original_game_animation_fidelity_verified"])

    def test_annotations_can_still_be_valid_but_rebinding_is_refused(self):
        receipt(*self.args)
        data = json.loads(self.observations.read_text())
        data["frames"][0]["landmarks"][0]["ps3_xy"][0] += .002
        self.observations.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            check(*self.args)

    def test_changed_binding_manifest_rejected_even_if_meaning_identical(self):
        receipt(*self.args)
        self.frame_bindings.write_text(
            json.dumps(json.loads(self.frame_bindings.read_text()),
                       indent=4) + "\n"
        )
        with self.assertRaises(ValueError):
            check(*self.args)

    def test_changed_synthetic_source_png_bytes_rejected(self):
        receipt(*self.args)
        (self.capture_dir / "frame_001.png").write_bytes(png(seed=179))
        with self.assertRaises(ValueError):
            check(*self.args)

    def test_reject_absent_source_image_and_unrecorded_capture(self):
        (self.capture_dir / "frame_002.png").unlink()
        with self.assertRaises((ValueError, OSError)):
            receipt(*self.args)
        self.assertFalse(self.output.exists())
        (self.capture_dir / "frame_002.png").write_bytes(png(seed=47))
        document = json.loads(self.observations.read_text())
        document["ps3_observation"]["capture_recorded"] = False
        self.observations.write_text(json.dumps(document))
        with self.assertRaises(ValueError):
            receipt(*self.args)
        self.assertFalse(self.output.exists())

    def test_receipt_cannot_overwrite_previous_record(self):
        receipt(*self.args)
        original = self.output.read_bytes()
        with self.assertRaises(ValueError):
            receipt(*self.args)
        self.assertEqual(self.output.read_bytes(), original)

    def test_symlinked_binding_receipt_cannot_be_reverified(self):
        receipt(*self.args)
        saved=self.output.with_name("saved-owner-receipt.json")
        self.output.rename(saved)
        self.output.symlink_to(saved)
        with self.assertRaises(ValueError):
            check(*self.args)
        self.assertTrue(saved.is_file())

    def test_cli_does_not_expose_private_images_paths_or_hashes(self):
        flags = [
            "--preview-root", str(self.previews),
            "--camera-lock", str(self.lock),
            "--stage203-root", str(self.final),
            "--observations", str(self.observations),
            "--frame-bindings", str(self.frame_bindings),
            "--source-manifest", str(self.source_manifest),
            "--source-dir", str(self.capture_dir),
            "--binding-receipt", str(self.output),
        ]
        buffer = StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(main(["--bind", *flags]), 0)
        self.assertEqual(json.loads(buffer.getvalue())["schema"], REPORT)
        self.assertNotIn(str(self.root), buffer.getvalue())
        self.assertNotIn("sha256", buffer.getvalue())
        with contextlib.redirect_stdout(StringIO()) as passed:
            self.assertEqual(main(["--verify", *flags]), 0)
        self.assertNotIn(str(self.root), passed.getvalue())
        failure = StringIO()
        with contextlib.redirect_stderr(failure):
            self.assertEqual(main(["--bind", *flags]), 2)
        self.assertNotIn(str(self.root), failure.getvalue())


if __name__ == "__main__":
    unittest.main()
