"""Stage245: reject incorrect parity pixels, invalid full-render timings and fraud."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from tools.foj_stage231_threat_guest_check import BACKGROUND,HERO,ENEMY,SIZE
from tools.foj_stage238_cache_guest_check import (
    STATES,EXPECTED_GENERATIONS,EXPECTED_HITS,
)
from tools.foj_stage241_render_guest_check import BIT_X,ON,OFF as ORIGINAL_OFF


def make_frame(path:Path,state:str,n:int) -> None:
    canvas=Image.new("RGB",SIZE,BACKGROUND)
    draw=ImageDraw.Draw(canvas)
    draw.rectangle((580,210,609,239),fill=HERO)
    draw.rectangle((780,310,809,339),fill=ENEMY)
    draw.rectangle((409,12,415,18),fill=EXPECTED_GENERATIONS[n])
    draw.rectangle((420,12,427,18),fill=EXPECTED_HITS[n])
    original_render_us=8000+n*23
    for bit,x in enumerate(BIT_X):
        draw.rectangle((x-1,12,x+1,18),
                       fill=ON if original_render_us&(1<<bit) else ORIGINAL_OFF)
    canvas.save(path)
from tools.foj_stage245_full_render_guest_check import (
    verify_full_render_pairs,center,BITS,CACHED_ON,UNCACHED_ON,OFF,READY,
)


def render_overlay(path:Path, cached:int, uncached:int,
                   *, bad_status:bool=False,bad_bit:bool=False) -> None:
    with Image.open(path) as input_image:
        image=input_image.convert("RGB")
    painter=ImageDraw.Draw(image)
    for framebuffer_x,value,color in ((780,cached,CACHED_ON),
                                      (852,uncached,UNCACHED_ON)):
        for i in range(BITS):
            center_x=center(framebuffer_x+4*i)
            painter.rectangle((center_x-1,12,center_x+1,18),
                              fill=color if value & (1<<i) else OFF)
    px=center(927)
    painter.rectangle((px-2,12,px+2,18),
                      fill=(255,34,34) if bad_status else READY)
    if bad_bit:
        x=center(780+4*13)
        painter.rectangle((x-1,12,x+1,18),fill=(240,0,0))
    image.save(path)


class FullRenderGuestTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.paths=tuple(Path(temp.name)/(s+".png") for s in STATES)
        for i,(path,state) in enumerate(zip(self.paths,STATES)):
            make_frame(path,state,i)
            render_overlay(path,8400+i*17,8750+i*19)

    def test_nine_frames_and_controls(self):
        result=verify_full_render_pairs(self.paths)
        self.assertEqual(result["captured_real_guest_frames"],9)
        self.assertEqual(result["guest_processes"],1)
        self.assertEqual(len(result["inactive_forecast_control_deltas_us"]),4)
        self.assertFalse(result["switch_fps_measured"])
        self.assertFalse(result["causal_whole_game_speedup_proven"])
        self.assertEqual(
            result["full_software_render_pairs"]["initial"]["cached_render_mean_us"],
            8400)

    def test_wrong_status_rejected(self):
        render_overlay(self.paths[1],8417,8769,bad_status=True)
        with self.assertRaises(ValueError):
            verify_full_render_pairs(self.paths)

    def test_damaged_high_timing_bit_rejected(self):
        render_overlay(self.paths[4],8468,8826,bad_bit=True)
        with self.assertRaises(ValueError):
            verify_full_render_pairs(self.paths)

    def test_zero_mean_rejected(self):
        render_overlay(self.paths[2],0,8788)
        with self.assertRaises(ValueError):
            verify_full_render_pairs(self.paths)

    def test_saturated_mean_rejected(self):
        render_overlay(self.paths[3],8434,65535)
        with self.assertRaises(ValueError):
            verify_full_render_pairs(self.paths)

    def test_missing_frame_rejected(self):
        with self.assertRaises(ValueError):
            verify_full_render_pairs(self.paths[:-1])


if __name__=="__main__":
    unittest.main()
