"""Generated-only guard screenshot fixtures for fail-closed NeXium proof."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from tools.foj_stage224_guard_guest_check import (
    PALETTE, compare_guard_frames
)


def image(path: Path, *, guarded: bool, active: bool = False,
          missing_enemy: bool = False, enemy_x: int = 360,
          blank: bool = False) -> None:
    frame = Image.new("RGB", (960, 600),
                      (0, 0, 0) if blank else PALETTE["background"])
    if not blank:
        brush = ImageDraw.Draw(frame)
        brush.rectangle((200, 210, 229, 239), fill=PALETTE["hero"])
        brush.rectangle((190, 160, 189+(35 if guarded else 30), 164),
                        fill=PALETTE["hero"])
        if not missing_enemy:
            brush.rectangle((enemy_x, 210, enemy_x+29, 239),
                            fill=PALETTE["enemy"])
        if active:
            brush.rectangle((234, 190, 240, 196),
                            fill=PALETTE["guard"])
    frame.save(path)


class Stage224GuestGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.paths = [root / f"shot{i}.png" for i in range(3)]
        self.make_valid()

    def make_valid(self) -> None:
        image(self.paths[0], guarded=True, active=True)
        image(self.paths[1], guarded=True)
        image(self.paths[2], guarded=False)

    def test_valid_two_guest_damage_outcomes(self) -> None:
        result = compare_guard_frames(*self.paths)
        self.assertEqual(result["guarded_minus_normal_hero_blue_pixels"], 25)
        self.assertTrue(result["guard_marker_seen_before_y"])

    def test_equal_damage_rejected(self) -> None:
        image(self.paths[2], guarded=True)
        with self.assertRaises(ValueError):
            compare_guard_frames(*self.paths)

    def test_missing_active_guard_rejected(self) -> None:
        image(self.paths[0], guarded=True)
        with self.assertRaises(ValueError):
            compare_guard_frames(*self.paths)

    def test_stale_guard_marker_rejected(self) -> None:
        image(self.paths[1], guarded=True, active=True)
        with self.assertRaises(ValueError):
            compare_guard_frames(*self.paths)

    def test_missing_enemy_rejected(self) -> None:
        image(self.paths[2], guarded=False, missing_enemy=True)
        with self.assertRaises(ValueError):
            compare_guard_frames(*self.paths)

    def test_mismatched_unit_positions_rejected(self) -> None:
        image(self.paths[2], guarded=False, enemy_x=460)
        with self.assertRaises(ValueError):
            compare_guard_frames(*self.paths)

    def test_blank_screen_rejected(self) -> None:
        image(self.paths[1], guarded=True, blank=True)
        with self.assertRaises(ValueError):
            compare_guard_frames(*self.paths)


if __name__ == "__main__":
    unittest.main()
