"""Stage241 fail-closed synthetic controls for NeXium timing-bar decoder."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.foj_stage231_threat_guest_check import BACKGROUND, HERO, ENEMY, SIZE
from tools.foj_stage238_cache_guest_check import (
    STATES, EXPECTED_GENERATIONS, EXPECTED_HITS,
)
from tools.foj_stage241_render_guest_check import (
    BIT_X, ON, OFF, PENDING, decode_microseconds, verify_render_timing,
)

SYNTHETIC_US = (3875, 4162, 3841, 3879, 4027, 3965, 3849, 3905, 3884)


def make_frame(path: Path, generation: tuple[int,int,int],
               hit: tuple[int,int,int], value: int,
               *, blank: bool=False, wrong_size: bool=False,
               pending_bit: int | None=None, bar_shift: int=0) -> None:
    if wrong_size:
        Image.new("RGB", (960,600), BACKGROUND).save(path)
        return
    canvas=Image.new("RGB", SIZE, (0,0,0) if blank else BACKGROUND)
    if not blank:
        draw=ImageDraw.Draw(canvas)
        draw.rectangle((580,210,609,239), fill=HERO)
        draw.rectangle((780,310,809,339), fill=ENEMY)
        draw.rectangle((409,12,415,18), fill=generation)
        draw.rectangle((420,12,427,18), fill=hit)
        for i,x in enumerate(BIT_X):
            color = PENDING if pending_bit == i else (
                ON if value & (1<<i) else OFF)
            draw.rectangle((x-1+bar_shift,12,x+1+bar_shift,18),fill=color)
    canvas.save(path)


class RenderTimingGuestEvidenceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.paths=tuple(Path(temp.name)/(state+".png") for state in STATES)
        self.reset()

    def reset(self):
        for path,gen,hit,value in zip(
                self.paths,EXPECTED_GENERATIONS,EXPECTED_HITS,SYNTHETIC_US):
            make_frame(path,gen,hit,value)

    def test_valid_timing_with_realistic_guest_state_sequence(self):
        result=verify_render_timing(self.paths)
        self.assertEqual(result["actual_guest_screenshots"],9)
        self.assertEqual(result["render_us_by_game_state"]["hovered"],3841)
        self.assertEqual(result["min_render_us"],3841)
        self.assertFalse(result["switch_fps_measured"])

    def test_pending_before_32_frames_rejected(self):
        make_frame(self.paths[0],EXPECTED_GENERATIONS[0],
                   EXPECTED_HITS[0],SYNTHETIC_US[0],pending_bit=3)
        with self.assertRaises(ValueError):
            verify_render_timing(self.paths)

    def test_zero_or_saturated_timing_rejected(self):
        for value in (0,65535):
            self.reset()
            make_frame(self.paths[2],EXPECTED_GENERATIONS[2],
                       EXPECTED_HITS[2],value)
            with self.assertRaises(ValueError):
                verify_render_timing(self.paths)

    def test_wrong_bit_color_rejected(self):
        with Image.open(self.paths[1]) as im:
            canvas=im.convert("RGB")
        draw=ImageDraw.Draw(canvas)
        x=BIT_X[7]
        draw.rectangle((x-1,12,x+1,18),fill=(220,0,0))
        canvas.save(self.paths[1])
        with self.assertRaises(ValueError):
            verify_render_timing(self.paths)

    def test_static_same_timing_rejected(self):
        for path,gen,hit in zip(
                self.paths,EXPECTED_GENERATIONS,EXPECTED_HITS):
            make_frame(path,gen,hit,3900)
        with self.assertRaises(ValueError):
            verify_render_timing(self.paths)

    def test_wrong_guest_battle_sequence_rejected(self):
        make_frame(self.paths[6],EXPECTED_GENERATIONS[0],
                   EXPECTED_HITS[6],SYNTHETIC_US[6])
        with self.assertRaises(ValueError):
            verify_render_timing(self.paths)

    def test_blank_guest_rejected(self):
        make_frame(self.paths[1],EXPECTED_GENERATIONS[1],
                   EXPECTED_HITS[1],SYNTHETIC_US[1],blank=True)
        with self.assertRaises(ValueError):
            verify_render_timing(self.paths)

    def test_wrong_resolution_rejected(self):
        make_frame(self.paths[1],EXPECTED_GENERATIONS[1],
                   EXPECTED_HITS[1],SYNTHETIC_US[1],wrong_size=True)
        with self.assertRaises(ValueError):
            verify_render_timing(self.paths)

    def test_shifted_timing_bars_rejected(self):
        make_frame(self.paths[2],EXPECTED_GENERATIONS[2],
                   EXPECTED_HITS[2],SYNTHETIC_US[2],bar_shift=5)
        with self.assertRaises(ValueError):
            verify_render_timing(self.paths)

    def test_missing_frame_rejected(self):
        with self.assertRaises(ValueError):
            verify_render_timing(self.paths[:-1])

    def test_missing_actual_screenshot_rejected(self):
        self.paths[8].unlink()
        with self.assertRaises(FileNotFoundError):
            verify_render_timing(self.paths)

    def test_not_confused_by_timing_colors_elsewhere(self):
        with Image.open(self.paths[1]) as im:
            canvas=im.convert("RGB")
        draw=ImageDraw.Draw(canvas)
        draw.rectangle((610,45,680,65),fill=ON)
        canvas.save(self.paths[1])
        result=verify_render_timing(self.paths)
        self.assertEqual(result["render_us_by_game_state"]["selected"],4162)


if __name__ == "__main__":
    unittest.main()
