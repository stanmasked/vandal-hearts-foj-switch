"""Stage250 mutate optical barcodes; all inherited Stage249 tests mandatory."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage250_scale_guest_check import (
    FIRST_X,STATUS_X,ON_COLORS,OFF,READY,verify_scale_guest,
)
from test_stage246_phase_guest_check import frame
from test_stage248_base_pair_guest_check import mark as stage248_mark
from test_stage249_stability_guest_check import paint as stage249_paint

def paint(path:Path,cold=(1000,4000,9000),warm=(90,350,820),status=READY):
    with Image.open(path) as original: im=original.convert("RGB")
    draw=ImageDraw.Draw(im)
    values=[v for pair in zip(cold,warm) for v in pair]
    for i,value in enumerate(values):
        origin=FIRST_X+i*72
        for bit in range(16):
            x=sample_x(origin+4*bit)
            draw.rectangle((x-1,28,x+1,34),
                           fill=ON_COLORS[i] if value&(1<<bit) else OFF)
    x=sample_x(STATUS_X+4)
    draw.rectangle((x-4,28,x+4,34),fill=status)
    im.save(path)

class Stage250ScaleGuestTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.paths=tuple(Path(t.name)/(s+".png") for s in STATES)
        for i,(state,path) in enumerate(zip(STATES,self.paths)):
            frame(path,i,state)
            stage248_mark(path,750+i,810+i)
            stage249_paint(path,cold=7000+i,warm=510+i,spread=230+i)
            paint(path,tuple(x+i for x in (1000,4000,9000)),
                       tuple(x+i for x in (90,350,820)))
    def test_nine_screens_all_prior_proofs(self):
        result=verify_scale_guest(self.paths)
        self.assertEqual(result["actual_game_states"],9)
        self.assertEqual(len(result["resolutions"]),3)
        self.assertEqual(result["resolutions"][0]["cold_active_median_us"],1004)
        self.assertEqual(result["resolutions"][2]["warm_active_median_us"],824)
        self.assertTrue(result["break_even_calculation_model_only"])
        self.assertFalse(result["whole_game_speedup_proven"])
    def test_bad_status_rejected(self):
        paint(self.paths[0],status=(0,0,0))
        with self.assertRaises(ValueError):verify_scale_guest(self.paths)
    def test_saturated_rejected(self):
        paint(self.paths[1],cold=(1000,65535,9000))
        with self.assertRaises(ValueError):verify_scale_guest(self.paths)
    def test_zero_rejected(self):
        paint(self.paths[2],warm=(90,0,820))
        with self.assertRaises(ValueError):verify_scale_guest(self.paths)
    def test_corrupt_bit_rejected(self):
        with Image.open(self.paths[3]) as original:im=original.convert("RGB")
        d=ImageDraw.Draw(im);x=sample_x(FIRST_X+3*72+4*10)
        d.rectangle((x-1,28,x+1,34),fill=(255,0,0));im.save(self.paths[3])
        with self.assertRaises(ValueError):verify_scale_guest(self.paths)
    def test_missing_image_rejected(self):
        with self.assertRaises(ValueError):verify_scale_guest(self.paths[:-1])
    def test_prior_stage249_mutation_rejected(self):
        with Image.open(self.paths[4]) as original:im=original.convert("RGB")
        d=ImageDraw.Draw(im);x=sample_x(536+4*5)
        d.rectangle((x-1,12,x+1,18),fill=(255,0,0));im.save(self.paths[4])
        with self.assertRaises(ValueError):verify_scale_guest(self.paths)

if __name__=="__main__":unittest.main()
