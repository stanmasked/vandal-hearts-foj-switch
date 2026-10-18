"""Stage235 generated-only screenshot regression for cursor-specific enemy landing."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.foj_stage235_landing_guest_check import verify_landing, MARKER
from tools.foj_stage231_threat_guest_check import (
    BACKGROUND, HERO, ENEMY, SIZE,
)


def frame(path:Path, *, marker=False, outside=False, blank=False,
          early=False, wrong_size=False) -> None:
    if wrong_size:
        Image.new("RGB",(960,600),BACKGROUND).save(path)
        return
    image=Image.new("RGB",SIZE,(0,0,0) if blank else BACKGROUND)
    if not blank:
        draw=ImageDraw.Draw(image)
        draw.rectangle((580,210,609,239),fill=HERO)
        draw.rectangle((780,310,809,339),fill=ENEMY)
        if marker or early:
            if outside:
                draw.rectangle((400,330,405,335),fill=MARKER)
            else:
                draw.rectangle((876,328,881,333),fill=MARKER)
    image.save(path)


class NextEnemyLandingEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.paths=tuple(Path(temp.name)/f"f{i}.png" for i in range(6))
        self.reset()

    def reset(self) -> None:
        for i,path in enumerate(self.paths):
            frame(path,marker=i in (2,4))

    def test_correct_enemy_destination_toggle_sequence(self):
        data=verify_landing(self.paths)
        self.assertEqual(data["expected_next_enemy_cell"],[6,2])

    def test_early_prediction_rejected(self):
        frame(self.paths[0],marker=True)
        with self.assertRaises(ValueError):verify_landing(self.paths)

    def test_prediction_before_cursor_selection_rejected(self):
        frame(self.paths[1],marker=True)
        with self.assertRaises(ValueError):verify_landing(self.paths)

    def test_missing_hovered_prediction_rejected(self):
        frame(self.paths[2],marker=False)
        with self.assertRaises(ValueError):verify_landing(self.paths)

    def test_hidden_prediction_not_hidden_rejected(self):
        frame(self.paths[3],marker=True)
        with self.assertRaises(ValueError):verify_landing(self.paths)

    def test_restored_prediction_missing_rejected(self):
        frame(self.paths[4],marker=False)
        with self.assertRaises(ValueError):verify_landing(self.paths)

    def test_blocked_cursor_stale_prediction_rejected(self):
        frame(self.paths[5],marker=True)
        with self.assertRaises(ValueError):verify_landing(self.paths)

    def test_wrong_enemy_tile_rejected(self):
        frame(self.paths[4],marker=True,outside=True)
        with self.assertRaises(ValueError):verify_landing(self.paths)

    def test_blank_guest_rejected(self):
        frame(self.paths[2],blank=True)
        with self.assertRaises(ValueError):verify_landing(self.paths)

    def test_wrong_guest_resolution_rejected(self):
        frame(self.paths[4],wrong_size=True)
        with self.assertRaises(ValueError):verify_landing(self.paths)


if __name__=="__main__":
    unittest.main()
