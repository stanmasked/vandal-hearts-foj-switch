"""Negative and positive *synthetic* fixtures for stage193 guest classifier."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.foj_stage193_animation_frame_check import COLORS, STATES, verify


class AnimationGuestClassifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.fixture()

    def path(self, name):
        return self.folder / f"anim-{name}.png"

    def fixture(self):
        offsets = {
            "initial": 0, "playing": 30, "paused": 30,
            "paused-later": 30, "fade-0": 0, "fade-25": 10,
            "fade-50": 20, "fade-75": 30, "fade-done": 40,
        }
        for name in STATES:
            image = Image.new("RGB", (800, 500), (37, 28, 24))
            brush = ImageDraw.Draw(image)
            brush.rectangle((10, 10, 60, 60), fill=COLORS["source"])
            clip = "clip_b" if name == "fade-done" else "clip_a"
            brush.rectangle((620, 10, 670, 60), fill=COLORS[clip])
            state = "playing" if name == "playing" else "paused"
            brush.rectangle((720, 10, 770, 60), fill=COLORS[state])
            if name.startswith("fade-") and name != "fade-done":
                brush.rectangle((560, 10, 610, 60), fill=COLORS["fade"])
                steps = {"fade-0": 0, "fade-25": 1,
                         "fade-50": 2, "fade-75": 3}[name]
                for i in range(steps):
                    brush.rectangle((80+50*i, 30, 119+50*i, 59),
                                    fill=COLORS["fade"])
            offset = offsets[name]
            brush.rectangle((320+offset, 170, 390+offset, 360),
                            outline=COLORS["wire"], width=3)
            image.save(self.path(name))

    def test_valid_animation_sequence(self):
        result = verify(self.folder)
        self.assertEqual(result["schema"],
                         "foj.stage193.generated_animation_guest.v1")
        self.assertEqual(len(result["states"]), 9)
        self.assertFalse(result["original_ps3_resources_used"])
        self.assertFalse(result["physical_switch_executed"])
        self.assertEqual(result["paused_stillness_delta"], 0)
        self.assertEqual(result["zero_weight_fade_delta"], 0)
        self.assertNotIn(str(self.folder), str(result))

    def mutate(self, name, action):
        path = self.path(name)
        image = Image.open(path).convert("RGB")
        action(image)
        image.save(path)

    def test_missing_frame_rejected(self):
        self.path("fade-50").unlink()
        with self.assertRaises(OSError):
            verify(self.folder)

    def test_wrong_active_clip_rejected(self):
        def corrupt(image):
            ImageDraw.Draw(image).rectangle(
                (620, 10, 670, 60), fill=COLORS["clip_a"])
        self.mutate("fade-done", corrupt)
        with self.assertRaisesRegex(ValueError, "Wrong active clip"):
            verify(self.folder)

    def test_pause_motion_rejected(self):
        def corrupt(image):
            ImageDraw.Draw(image).rectangle(
                (320, 170, 460, 360), fill=(37, 28, 24))
            ImageDraw.Draw(image).rectangle(
                (390, 170, 460, 360), outline=COLORS["wire"], width=3)
        self.mutate("paused-later", corrupt)
        with self.assertRaisesRegex(ValueError, "Paused clip changed"):
            verify(self.folder)

    def test_empty_fade_progress_rejected(self):
        def corrupt(image):
            ImageDraw.Draw(image).rectangle(
                (560, 10, 610, 60), fill=(37, 28, 24))
        self.mutate("fade-0", corrupt)
        with self.assertRaisesRegex(ValueError, "Wrong crossfade"):
            verify(self.folder)

    def test_static_geometry_rejected(self):
        self.path("fade-25").write_bytes(self.path("fade-0").read_bytes())
        with self.assertRaises(ValueError):
            verify(self.folder)

    def test_missing_source_marker_rejected(self):
        def corrupt(image):
            ImageDraw.Draw(image).rectangle(
                (10, 10, 60, 60), fill=(37, 28, 24))
        self.mutate("initial", corrupt)
        with self.assertRaisesRegex(ValueError, "Synthetic source"):
            verify(self.folder)

    def test_small_frame_rejected(self):
        Image.new("RGB", (200, 100)).save(self.path("initial"))
        with self.assertRaisesRegex(ValueError, "too small"):
            verify(self.folder)


if __name__ == "__main__":
    unittest.main()
