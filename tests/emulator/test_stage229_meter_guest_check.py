"""Synthetic screenshot fixture tests for Stage229 input replay meter."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from tools.foj_stage229_meter_guest_check import verify_meter

BG=(13,19,33); HERO=(95,193,244); ENEMY=(227,82,93)
UNDO=(113,241,201); METER=(57,161,229)


def draw_frame(file: Path, hero_x: int, commands: int,
               *, marker: bool=False, enemy_x: int=390) -> None:
    im=Image.new("RGB",(960,600),BG)
    p=ImageDraw.Draw(im)
    p.rectangle((hero_x,210,hero_x+29,239),fill=HERO)
    p.rectangle((hero_x-10,170,hero_x+25,174),fill=HERO)
    p.rectangle((enemy_x,220,enemy_x+29,249),fill=ENEMY)
    if marker:
        p.rectangle((hero_x-35,190,hero_x-28,196),fill=UNDO)
    if commands:
        p.rectangle((420,80,419+commands,87),fill=METER)
    im.save(file)


class Stage229GuestMeterTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.files=tuple(Path(tmp.name)/f"f{i}.png" for i in range(4))
        self.fixture()

    def fixture(self) -> None:
        draw_frame(self.files[0],200,0)
        draw_frame(self.files[1],290,4,marker=True)
        draw_frame(self.files[2],200,5)
        draw_frame(self.files[3],245,8,marker=True)

    def test_valid_counts(self) -> None:
        report=verify_meter(self.files)
        self.assertEqual(report["expected_input_counts"],[0,4,5,8])

    def test_missing_action_count_rejected(self) -> None:
        draw_frame(self.files[1],290,0,marker=True)
        with self.assertRaises(ValueError): verify_meter(self.files)

    def test_b_missing_from_history_rejected(self) -> None:
        draw_frame(self.files[2],200,4)
        with self.assertRaises(ValueError): verify_meter(self.files)

    def test_alternate_route_count_tampered(self) -> None:
        draw_frame(self.files[3],245,7,marker=True)
        with self.assertRaises(ValueError): verify_meter(self.files)

    def test_fake_initial_log_rejected(self) -> None:
        draw_frame(self.files[0],200,5)
        with self.assertRaises(ValueError): verify_meter(self.files)

    def test_static_hero_rejected_despite_valid_counter(self) -> None:
        draw_frame(self.files[1],200,4,marker=True)
        with self.assertRaises(ValueError): verify_meter(self.files)


if __name__ == "__main__":
    unittest.main()
