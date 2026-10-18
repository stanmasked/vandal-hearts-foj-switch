"""Synthetic negative tests of the stage-184 NeXium guest image auditor.

These are generated PIL shapes, never misrepresented as real emulator frames.
"""
from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.foj_stage184_coll_input_check import (
    STATES, SCHEMA, verify_input_sequence,
)


class Stage184InputFrameTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.root=Path(self.folder.name)
        self.prev=self.root/"coll-heat-return-after-y.png"
        self.captures={}
        self.references={}
        self.frame((37,62,79)).save(self.prev)
        palette=[
            (80,110,151), (158,110,56),
            (75,168,108), (184,62,112), (98,70,192),
            (218,92,108), (46,66,79), (158,110,56),
        ]
        for state,color in zip(STATES,palette,strict=True):
            guest=self.root/f"{state}.png"
            reference=self.root/f"ref-{state}.png"
            self.frame(color).save(guest)
            self.frame(color).save(reference)
            self.captures[state]=guest
            self.references[state]=reference

    def tearDown(self):
        self.folder.cleanup()

    @staticmethod
    def frame(color):
        frame=Image.new("RGB",(1280,720),(17,22,34))
        draw=ImageDraw.Draw(frame)
        draw.rectangle((280,100,1000,645),fill=color)
        draw.rectangle((1235,16,1261,34),fill=(231,94,86))
        return frame

    def check(self):
        return verify_input_sequence(self.prev,self.captures,self.references)

    def test_all_input_states_valid_and_no_physical_claim(self):
        receipt=self.check()
        self.assertEqual(receipt["schema"],SCHEMA)
        self.assertEqual(len(receipt["states_verified"]),8)
        self.assertEqual(receipt["pixels_changed_after_six_channel_wrap"],0)
        self.assertTrue(receipt["observed_six_raw_channel_cycle"])
        self.assertFalse(receipt["physical_switch_execution_verified"])
        self.assertNotIn(str(self.root),str(receipt))

    def test_nearest_neighbor_scaled_emulator_window_matches_unscaled_c(self):
        # NeXium places a scaled guest framebuffer above desktop controls.
        # Host C reference remains 1280x720. Simulate 96.3% guest scale.
        for path in [self.prev, *self.captures.values()]:
            with Image.open(path) as image:
                scaled = image.convert("RGB").resize(
                    (1232, 694), Image.Resampling.NEAREST)
            window = Image.new("RGB", (1280, 720), (12, 17, 30))
            window.paste(scaled, (24, 0))
            window.save(path)
        receipt = self.check()
        self.assertEqual(len(receipt["host_c_reference_matches"]), 8)
        self.assertFalse(receipt["physical_gpu_scanout_verified"])

    def test_static_cursor_screen_rejected(self):
        Image.open(self.prev).save(self.captures["cursor-right"])
        with self.assertRaises(ValueError):
            self.check()

    def test_wrong_channel_image_rejected(self):
        Image.open(self.captures["ch2"]).save(self.captures["ch3"])
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_synthetic_marker_rejected(self):
        frame=self.frame((75,168,108))
        ImageDraw.Draw(frame).rectangle((1235,16,1261,34),fill=(17,22,34))
        frame.save(self.captures["ch1"])
        with self.assertRaises(ValueError):
            self.check()

    def test_channel_wrap_not_restored_rejected(self):
        Image.open(self.captures["ch5"]).save(self.captures["ch0"])
        with self.assertRaises(ValueError):
            self.check()

    def test_reference_wrong_resolution_rejected(self):
        Image.new("RGB",(32,32)).save(self.references["zoom"])
        with self.assertRaises(ValueError):
            self.check()


if __name__=="__main__":
    unittest.main()
