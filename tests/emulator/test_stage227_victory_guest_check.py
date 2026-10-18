"""Generated-only positive and negative cases for Stage227 guest screenshot verifier."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from tools.foj_stage227_victory_guest_check import PALETTE, verify_victory


def screenshot(path: Path, *, hero_hp: int = 8, enemy_hp: int = 6,
               win: bool = False, empty: bool = False) -> None:
    image = Image.new("RGB", (960, 600),
                      (0, 0, 0) if empty else PALETTE["background"])
    if not empty:
        draw = ImageDraw.Draw(image)
        draw.rectangle((150, 210, 179, 239), fill=PALETTE["hero"])
        if hero_hp:
            draw.rectangle((150, 170, 149+hero_hp*5, 174),
                           fill=PALETTE["hero"])
        if enemy_hp:
            draw.rectangle((350, 220, 379, 249), fill=PALETTE["enemy"])
            draw.rectangle((350, 170, 349+enemy_hp*5, 174),
                           fill=PALETTE["enemy"])
        if win:
            draw.rectangle((0, 0, 959, 7), fill=PALETTE["victory"])
    image.save(path)


class Stage227VictoryScreenshotTests(unittest.TestCase):
    def setUp(self) -> None:
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.frames = tuple(Path(work.name)/f"capture-{i}.png"
                            for i in range(6))
        self.fixture()

    def fixture(self) -> None:
        screenshot(self.frames[0], hero_hp=8, enemy_hp=6)
        screenshot(self.frames[1], hero_hp=6, enemy_hp=6)
        screenshot(self.frames[2], hero_hp=6, enemy_hp=3)
        screenshot(self.frames[3], hero_hp=4, enemy_hp=3)
        screenshot(self.frames[4], hero_hp=4, enemy_hp=0, win=True)
        screenshot(self.frames[5], hero_hp=4, enemy_hp=0, win=True)

    def test_valid_synthetic_full_playthrough(self) -> None:
        result = verify_victory(self.frames)
        self.assertTrue(result["second_x_resulted_in_victory"])
        self.assertTrue(result["terminal_y_was_rejected"])

    def test_first_x_does_not_reduce_enemy_hp(self) -> None:
        screenshot(self.frames[2], hero_hp=6, enemy_hp=6)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_second_y_does_not_hurt_hero(self) -> None:
        screenshot(self.frames[3], hero_hp=6, enemy_hp=3)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_first_y_does_not_hurt_hero(self) -> None:
        screenshot(self.frames[1], hero_hp=8, enemy_hp=6)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_hero_loses_hp_during_own_attack(self) -> None:
        screenshot(self.frames[2], hero_hp=4, enemy_hp=3)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_victory_green_strip_missing(self) -> None:
        screenshot(self.frames[4], hero_hp=4, enemy_hp=0)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_enemy_not_removed_on_victory(self) -> None:
        screenshot(self.frames[4], hero_hp=4, enemy_hp=3, win=True)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_early_fake_victory_is_rejected(self) -> None:
        screenshot(self.frames[2], hero_hp=6, enemy_hp=3, win=True)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_terminal_turn_changes_hp(self) -> None:
        screenshot(self.frames[5], hero_hp=2, enemy_hp=0, win=True)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_blank_guest_frame(self) -> None:
        screenshot(self.frames[1], empty=True)
        with self.assertRaises(ValueError):
            verify_victory(self.frames)

    def test_mismatched_screen_dimensions(self) -> None:
        Image.new("RGB", (810, 530), PALETTE["background"]).save(self.frames[5])
        with self.assertRaises(ValueError):
            verify_victory(self.frames)


if __name__ == "__main__":
    unittest.main()
