"""Generated-only negative/positive tests for real guest movement verifier."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.foj_stage223_battle_guest_check import (
    BACKGROUND, ENEMY, HERO, check_frames
)


def frame(path: Path, ex: int, ey: int = 235,
          *, missing_hero: bool = False, blank: bool = False) -> None:
    image = Image.new("RGB", (960, 600), (0, 0, 0) if blank else BACKGROUND)
    if not blank:
        draw = ImageDraw.Draw(image)
        if not missing_hero:
            draw.rectangle((180, 205, 205, 230), fill=HERO)
        draw.rectangle((ex, ey, ex+25, ey+25), fill=ENEMY)
    image.save(path)


class Stage223BattleGuestVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = tempfile.TemporaryDirectory()
        self.addCleanup(self.context.cleanup)
        root = Path(self.context.name)
        self.paths = (root/"initial.png", root/"after-one.png",
                      root/"after-two.png")

    def prepare(self) -> None:
        for path, x in zip(self.paths, [380, 330, 280]):
            frame(path, x)

    def test_two_distinct_realistic_turn_positions_pass(self) -> None:
        self.prepare()
        result = check_frames(self.paths)
        self.assertTrue(result["guest_enemy_moves_after_y"])
        self.assertEqual(result["screenshots_compared"], 3)
        self.assertEqual(len(result["enemy_displacement_after_each_emulated_y"]), 2)

    def test_static_guest_frames_fail(self) -> None:
        for path in self.paths:
            frame(path, 380)
        with self.assertRaises(ValueError):
            check_frames(self.paths)

    def test_blank_frame_fail(self) -> None:
        self.prepare()
        frame(self.paths[1], 100, blank=True)
        with self.assertRaises(ValueError):
            check_frames(self.paths)

    def test_missing_hero_fail(self) -> None:
        self.prepare()
        frame(self.paths[2], 280, missing_hero=True)
        with self.assertRaises(ValueError):
            check_frames(self.paths)

    def test_implausible_enemy_teleport_fails(self) -> None:
        self.prepare()
        frame(self.paths[1], 850, 500)
        with self.assertRaises(ValueError):
            check_frames(self.paths)

    def test_mismatched_dimensions_fail(self) -> None:
        self.prepare()
        Image.new("RGB", (800, 500), BACKGROUND).save(self.paths[2])
        with self.assertRaises(ValueError):
            check_frames(self.paths)


if __name__ == "__main__":
    unittest.main()
