"""Generated-only screenshot classification tests, requiring Pillow.

Only invoked in stage182 emulator runner, not the base Python test matrix.
These locally synthesized screenshots are tests of the classifier, NOT
emulator runtime evidence.
"""
from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.foj_stage182_nexium_frame_check import (
    COLORS, SCHEMA, verify_emulator_captures,
)


class Stage182FrameClassifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.initial = self.directory / "initial.png"
        self.after = self.directory / "route.png"
        self.coll = self.directory / "coll.png"
        self.write_positive_fixture()

    def tearDown(self):
        self.tmp.cleanup()

    def write_positive_fixture(self):
        initial = Image.new("RGB", (800, 500), COLORS["iso_background"])
        brush = ImageDraw.Draw(initial)
        brush.rectangle((100, 100, 130, 130), fill=COLORS["iso_hero"])
        brush.rectangle((300, 300, 330, 330), fill=COLORS["iso_enemy"])
        initial.save(self.initial)

        route = initial.copy()
        brush = ImageDraw.Draw(route)
        brush.rectangle((190, 180, 203, 193), fill=COLORS["iso_route"])
        route.save(self.after)

        col = Image.new("RGB", (800, 500), COLORS["coll_background"])
        brush = ImageDraw.Draw(col)
        brush.rectangle((720, 15, 750, 34), fill=COLORS["coll_synthetic"])
        brush.rectangle((410, 210, 430, 230), fill=COLORS["coll_cursor"])
        col.save(self.coll)

    def test_two_guest_frame_shapes_and_route_color(self):
        result = verify_emulator_captures(self.initial, self.after, self.coll)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertTrue(result["isometric_initial_visible"])
        self.assertTrue(result["isometric_route_after_emulated_input_visible"])
        self.assertTrue(result["coll_generated_fallback_visible"])
        self.assertGreater(result["isometric_route_pixels_after_input"], 30)
        for key in ("physical_switch_execution_verified",
                    "original_foj_gameplay_verified",
                    "gpu_scanout_on_physical_switch_verified"):
            self.assertFalse(result[key])
        self.assertFalse(result["original_ps3_assets_used"])
        self.assertNotIn(str(self.directory), str(result))

    def test_does_not_accept_unchanged_guest_frame(self):
        with self.assertRaises(ValueError):
            verify_emulator_captures(self.initial, self.initial, self.coll)

    def test_does_not_accept_blank_window(self):
        Image.new("RGB", (800, 500), (0, 0, 0)).save(self.initial)
        with self.assertRaises(ValueError):
            verify_emulator_captures(self.initial, self.after, self.coll)

    def test_does_not_accept_coll_screen_without_synthetic_marker(self):
        Image.new("RGB", (800, 500), COLORS["coll_background"]).save(self.coll)
        with self.assertRaises(ValueError):
            verify_emulator_captures(self.initial, self.after, self.coll)

    def test_tiny_or_changed_dimensions_rejected(self):
        Image.new("RGB", (64, 64), COLORS["iso_background"]).save(self.initial)
        with self.assertRaises(ValueError):
            verify_emulator_captures(self.initial, self.after, self.coll)
        self.write_positive_fixture()
        Image.new("RGB", (810, 500), COLORS["iso_background"]).save(self.after)
        with self.assertRaises(ValueError):
            verify_emulator_captures(self.initial, self.after, self.coll)


if __name__ == "__main__":
    unittest.main()
