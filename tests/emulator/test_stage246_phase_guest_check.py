"""Stage246: detect forged exclusive software-raster phase screenshots."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage231_threat_guest_check import BACKGROUND,HERO,ENEMY,SIZE
from tools.foj_stage238_cache_guest_check import (
    STATES,EXPECTED_GENERATIONS,EXPECTED_HITS,
)
from tools.foj_stage241_render_guest_check import BIT_X,ON,OFF
from tools.foj_stage246_phase_guest_check import (
    PHASES,X,COLORS,READY,sample_x,verify_phase_screenshots
)

def frame(path:Path,n:int,state:str) -> None:
    canvas=Image.new("RGB",SIZE,BACKGROUND)
    draw=ImageDraw.Draw(canvas)
    draw.rectangle((580,210,609,239),fill=HERO)
    draw.rectangle((780,310,809,339),fill=ENEMY)
    draw.rectangle((409,12,415,18),fill=EXPECTED_GENERATIONS[n])
    draw.rectangle((420,12,427,18),fill=EXPECTED_HITS[n])
    for bit,x in enumerate(BIT_X):
        draw.rectangle((x-1,12,x+1,18),
                       fill=ON if (8000+n*23)&(1<<bit) else OFF)
    values=(6100+n*17,290 if state in
            ("selected","hovered","restored","guarded","guard_hovered")
            else 0,75 if state in
            ("selected","hovered","restored","guarded","guard_hovered")
            else 0,130+n)
    for origin,color,value in zip(X,COLORS,values):
        for bit in range(16):
            x=sample_x(origin+bit*4)
            draw.rectangle((x-1,12,x+1,18),
                           fill=color if value&(1<<bit) else OFF)
    x=sample_x(1241)
    draw.rectangle((x-4,12,x+4,18),fill=READY)
    canvas.save(path)

class PhaseGuestChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.paths=tuple(Path(temp.name)/(s+".png") for s in STATES)
        for n,(s,p) in enumerate(zip(STATES,self.paths)):
            frame(p,n,s)

    def test_ordered_nine_frames_and_controls(self):
        result=verify_phase_screenshots(self.paths)
        self.assertEqual(result["captured_game_screenshots"],9)
        self.assertEqual(result["states"]["selected"]["terrain"],6117)
        self.assertEqual(result["states"]["initial"]["forecast_compute"],0)
        self.assertFalse(result["switch_fps_measured"])
        self.assertFalse(result["overall_game_speedup_proven"])
        self.assertEqual(len(result["exclusive_timing_phases"]),4)

    def test_wrong_status_rejected(self):
        with Image.open(self.paths[1]) as x: im=x.convert("RGB")
        painter=ImageDraw.Draw(im)
        x=sample_x(1241)
        painter.rectangle((x-4,12,x+4,18),fill=(255,34,34))
        im.save(self.paths[1])
        with self.assertRaises(ValueError):
            verify_phase_screenshots(self.paths)

    def test_corrupt_high_bit_rejected(self):
        with Image.open(self.paths[4]) as x: im=x.convert("RGB")
        painter=ImageDraw.Draw(im)
        x=sample_x(X[3]+4*14)
        painter.rectangle((x-1,12,x+1,18),fill=(244,0,10))
        im.save(self.paths[4])
        with self.assertRaises(ValueError):
            verify_phase_screenshots(self.paths)

    def test_missing_image_rejected(self):
        with self.assertRaises(ValueError):
            verify_phase_screenshots(self.paths[:-1])

    def test_saturated_bar_rejected(self):
        with Image.open(self.paths[2]) as x: im=x.convert("RGB")
        painter=ImageDraw.Draw(im)
        for bit in range(16):
            x=sample_x(X[1]+4*bit)
            painter.rectangle((x-1,12,x+1,18),fill=COLORS[1])
        im.save(self.paths[2])
        with self.assertRaises(ValueError):
            verify_phase_screenshots(self.paths)

    def test_invalid_original_cache_state_rejected(self):
        with Image.open(self.paths[6]) as x: im=x.convert("RGB")
        painter=ImageDraw.Draw(im)
        painter.rectangle((409,12,415,18),fill=(255,0,0))
        im.save(self.paths[6])
        with self.assertRaises(ValueError):
            verify_phase_screenshots(self.paths)

if __name__=="__main__":
    unittest.main()
