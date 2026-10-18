"""Synthetic fixture regressions; not NeXium runtime evidence."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage186_coll_boundary_check import (
    SCHEMA, STATES, verify_bounds,
)


class Stage186BoundaryChecker(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        palette = (
            (72, 111, 160), (188, 106, 80), (78, 154, 110),
            (185, 76, 125), (111, 80, 186), (172, 146, 62),
        )
        self._picture((42, 55, 80)).save(self.root / "coll-reverse-left.png")
        for (name, _x, _y, _tile), color in zip(STATES, palette, strict=True):
            picture = self._picture(color)
            picture.save(self.root / f"coll-{name}.png")
            picture.save(self.root / f"coll-{name}-repeat.png")
            picture.save(self.root / f"ref-coll-{name}.png")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _picture(color):
        picture = Image.new("RGB", (1280, 720), (17, 22, 34))
        brush = ImageDraw.Draw(picture)
        brush.rectangle((250, 80, 1050, 655), fill=color)
        brush.rectangle((1235, 16, 1261, 34), fill=(231, 94, 86))
        return picture

    def test_all_six_clamps_and_no_physical_claim(self):
        result = verify_bounds(self.root)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(len(result["states_verified"]), 6)
        self.assertEqual(result["verified_cursor_maximum"], [49, 49])
        self.assertEqual(result["verified_tile_size_minimum"], 4)
        self.assertFalse(result["physical_switch_execution_verified"])
        self.assertFalse(result["authentic_foj_collision_semantics_verified"])
        self.assertNotIn(str(self.root), str(result))

    def test_repeat_at_boundary_that_moves_rejected(self):
        self._picture((210, 62, 90)).save(
            self.root / "coll-right-edge-repeat.png")
        with self.assertRaises(ValueError):
            verify_bounds(self.root)

    def test_first_action_does_not_change_rejected(self):
        Image.open(self.root / "coll-reverse-left.png").save(
            self.root / "coll-left-edge.png")
        with self.assertRaises(ValueError):
            verify_bounds(self.root)

    def test_incorrect_zoom_reference_rejected(self):
        Image.open(self.root / "ref-coll-max-zoom.png").save(
            self.root / "ref-coll-min-zoom.png")
        with self.assertRaises(ValueError):
            verify_bounds(self.root)

    def test_missing_marker_rejected(self):
        self._picture((78, 154, 110)).save(
            self.root / "coll-min-zoom.png")
        altered = Image.new("RGB", (1280, 720), (17, 22, 34))
        ImageDraw.Draw(altered).rectangle(
            (250, 80, 1050, 655), fill=(78, 154, 110))
        altered.save(self.root / "coll-min-zoom.png")
        with self.assertRaises(ValueError):
            verify_bounds(self.root)

    def test_missing_screenshot_rejected(self):
        (self.root / "coll-top-edge-repeat.png").unlink()
        with self.assertRaises((OSError, ValueError)):
            verify_bounds(self.root)


if __name__ == "__main__":
    unittest.main()
