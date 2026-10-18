"""Generated-only expected/negative tests for real NeXium risk-preview judge."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from tools.foj_stage231_threat_guest_check import (
    BACKGROUND, HERO, ENEMY, SAFE, DANGER, PIXELS, SIZE, check_preview,
)


def fixture(path: Path, selected: bool, *, guard: bool = False,
            wrong_safe: bool = False, stale: bool = False,
            second_bar: bool = False, blank: bool = False) -> None:
    image=Image.new("RGB",SIZE, (0,0,0) if blank else BACKGROUND)
    if not blank:
        brush=ImageDraw.Draw(image)
        brush.rectangle((580,210,609,239),fill=HERO)
        brush.rectangle((780,310,809,339),fill=ENEMY)
        if selected or stale:
            if not wrong_safe:
                image.putpixel(PIXELS["safe"], SAFE)
            image.putpixel(PIXELS["damage_one"],DANGER)
            if not guard or second_bar:
                image.putpixel(PIXELS["damage_two"],DANGER)
    image.save(path)


class Stage231GuestPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.frames=tuple(Path(temp.name)/f"frame{i}.png" for i in range(5))
        self.make_valid()

    def make_valid(self) -> None:
        fixture(self.frames[0],False)
        fixture(self.frames[1],True)
        fixture(self.frames[2],True)
        fixture(self.frames[3],False)
        fixture(self.frames[4],True,guard=True)

    def test_generated_expected_sequence(self) -> None:
        report=check_preview(self.frames)
        self.assertTrue(report["guard_reduces_expected_damage_to_one_hp"])

    def test_missing_safe_preview_fails(self) -> None:
        fixture(self.frames[1],True,wrong_safe=True)
        with self.assertRaises(ValueError): check_preview(self.frames)

    def test_danger_disappears_while_cursor_moves_fails(self) -> None:
        fixture(self.frames[2],False)
        with self.assertRaises(ValueError): check_preview(self.frames)

    def test_stale_preview_after_b_fails(self) -> None:
        fixture(self.frames[3],False,stale=True)
        with self.assertRaises(ValueError): check_preview(self.frames)

    def test_false_guard_reduction_fails(self) -> None:
        fixture(self.frames[4],True,guard=True,second_bar=True)
        with self.assertRaises(ValueError): check_preview(self.frames)

    def test_blank_guest_frame_fails(self) -> None:
        fixture(self.frames[1],False,blank=True)
        with self.assertRaises(ValueError): check_preview(self.frames)

    def test_mismatch_guest_size_fails(self) -> None:
        Image.new("RGB",(960,600),BACKGROUND).save(self.frames[4])
        with self.assertRaises(ValueError): check_preview(self.frames)

    def test_preview_present_before_select_fails(self) -> None:
        fixture(self.frames[0],True)
        with self.assertRaises(ValueError): check_preview(self.frames)


if __name__ == "__main__":
    unittest.main()
