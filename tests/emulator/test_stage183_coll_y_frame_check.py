"""Synthetic negative regressions for Stage 183 screenshot classifier.

These invented images test the checker. They are NOT NeXium runtime proof;
the workflow separately captures real NRO guest pixels.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.foj_stage183_coll_y_frame_check import verify_mode_roundtrip, SCHEMA


class TestCollModeRoundtrip(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.p = Path(self.t.name)
        self.a = self.p / "heat.png"
        self.b = self.p / "iso.png"
        self.c = self.p / "heat-return.png"
        self.rh = self.p / "ref-heat.png"
        self.ri = self.p / "ref-iso.png"
        heat = Image.new("RGB", (1280, 720), (17, 22, 34))
        iso = Image.new("RGB", (1280, 720), (16, 22, 35))
        # A real mode change affects the map geometry, not just
        # background RGB by 1. Model a large mode-specific data region.
        ImageDraw.Draw(heat).rectangle(
            (90, 85, 350, 250), fill=(52, 97, 151))
        ImageDraw.Draw(iso).rectangle(
            (90, 85, 350, 250), fill=(161, 100, 72))
        for img, cursor in ((heat, (255, 232, 140)),
                            (iso, (255, 224, 118))):
            draw = ImageDraw.Draw(img)
            draw.rectangle((1235, 16, 1261, 34), fill=(231, 94, 86))
            draw.rectangle((630, 350, 650, 370), fill=cursor)
        heat.save(self.rh)
        heat.save(self.a)
        heat.save(self.c)
        iso.save(self.ri)
        iso.save(self.b)

    def tearDown(self):
        self.t.cleanup()

    def check(self):
        return verify_mode_roundtrip(self.a, self.b, self.c, self.rh, self.ri)

    def test_generated_classifier_roundtrip(self):
        receipt = self.check()
        self.assertEqual(receipt["schema"], SCHEMA)
        self.assertGreater(receipt["changed_pixels_first_toggle"], 10000)
        self.assertEqual(receipt["changed_pixels_after_roundtrip"], 0)
        self.assertTrue(receipt["isometric_matches_host_reference"])
        self.assertFalse(receipt["physical_switch_execution_verified"])
        self.assertNotIn(str(self.p), str(receipt))

    def test_static_after_y_rejected(self):
        Image.open(self.a).save(self.b)
        with self.assertRaises(ValueError):
            self.check()

    def test_first_capture_is_isometric_rejected(self):
        Image.open(self.b).save(self.a)
        with self.assertRaises(ValueError):
            self.check()

    def test_no_return_to_2d_rejected(self):
        Image.open(self.b).save(self.c)
        with self.assertRaises(ValueError):
            self.check()

    def test_missing_synthetic_marker_rejected(self):
        wrong = Image.new("RGB", (1280, 720), (16, 22, 35))
        ImageDraw.Draw(wrong).rectangle(
            (630, 350, 650, 370), fill=(255, 224, 118))
        wrong.save(self.b)
        with self.assertRaises(ValueError):
            self.check()

    def test_malformed_reference_or_dimensions_rejected(self):
        Image.new("RGB", (64, 64), (17, 22, 34)).save(self.rh)
        with self.assertRaises(ValueError):
            self.check()

    def test_wrong_reference_for_isometric_rejected(self):
        Image.open(self.rh).save(self.ri)
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
