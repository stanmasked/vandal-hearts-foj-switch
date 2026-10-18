"""Generated-only regression cases for the Stage226 guest screenshot checker."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.foj_stage226_undo_guest_check import COLORS, verify_undo


def image(path: Path, hx: int, *, marker: bool = False,
          enemy_x: int = 390, blank: bool = False,
          width: int = 960, height: int = 600) -> None:
    frame = Image.new("RGB", (width, height),
                      (0, 0, 0) if blank else COLORS["background"])
    if not blank:
        draw = ImageDraw.Draw(frame)
        draw.rectangle((hx, 210, hx+29, 239), fill=COLORS["hero"])
        draw.rectangle((hx-10, 170, hx+25, 174), fill=COLORS["hero"])
        draw.rectangle((enemy_x, 220, enemy_x+29, 249),
                       fill=COLORS["enemy"])
        if marker:
            draw.rectangle((hx-35, 190, hx-28, 196),
                           fill=COLORS["can_undo"])
    frame.save(path)


class MovementUndoGuestTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.files = tuple(Path(folder.name)/f"frame{i}.png"
                           for i in range(4))
        self.reset()

    def reset(self) -> None:
        image(self.files[0], 200)
        image(self.files[1], 290, marker=True)
        image(self.files[2], 200)
        image(self.files[3], 245, marker=True)

    def test_valid_realistic_b_undo_sequence(self) -> None:
        report = verify_undo(self.files)
        self.assertTrue(report["initial_hero_restored_after_b"])
        self.assertTrue(report["alternate_route_accepted"])

    def test_static_move_rejected(self) -> None:
        image(self.files[1], 200, marker=True)
        with self.assertRaises(ValueError):
            verify_undo(self.files)

    def test_undo_missing_rejected(self) -> None:
        image(self.files[2], 245)
        with self.assertRaises(ValueError):
            verify_undo(self.files)

    def test_marker_not_removed_rejected(self) -> None:
        image(self.files[2], 200, marker=True)
        with self.assertRaises(ValueError):
            verify_undo(self.files)

    def test_alternate_move_missing_rejected(self) -> None:
        image(self.files[3], 200, marker=True)
        with self.assertRaises(ValueError):
            verify_undo(self.files)

    def test_enemy_motion_rejected(self) -> None:
        image(self.files[3], 245, marker=True, enemy_x=470)
        with self.assertRaises(ValueError):
            verify_undo(self.files)

    def test_blank_frame_rejected(self) -> None:
        image(self.files[1], 290, blank=True)
        with self.assertRaises(ValueError):
            verify_undo(self.files)

    def test_mismatched_dimensions_rejected(self) -> None:
        image(self.files[2], 200, width=800, height=500)
        with self.assertRaises(ValueError):
            verify_undo(self.files)


if __name__ == "__main__":
    unittest.main()
