"""Stage248 reject missing, saturated, ambiguous A/B raster evidence."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage247_base_cache_guest_check import HIT_RGB,TILE_X
from tools.foj_stage248_base_pair_guest_check import (
    PAIR_X,BAR_COLOR,BAR_OFF,STATUS_X,STATUS_READY,
    verify_base_pair_guest,
)
from test_stage246_phase_guest_check import frame

def mark(path, cached=750,uncached=810,status=STATUS_READY):
    with Image.open(path) as original:
        image=original.convert("RGB")
    draw=ImageDraw.Draw(image)
    draw.rectangle((sample_x(TILE_X+1),12,sample_x(TILE_X+7),18),fill=HIT_RGB)
    for origin,color,value in zip(PAIR_X,BAR_COLOR,(cached,uncached)):
        for bit in range(16):
            x=sample_x(origin+4*bit)
            draw.rectangle((x-1,12,x+1,18),
                           fill=color if (value&(1<<bit)) else BAR_OFF)
    x=sample_x(STATUS_X+4)
    draw.rectangle((x-4,12,x+4,18),fill=status)
    image.save(path)

class Stage248BasePairGuestTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.paths=tuple(Path(temp.name)/(state+".png") for state in STATES)
        for n,(state,path) in enumerate(zip(STATES,self.paths)):
            frame(path,n,state)
            mark(path,750+n,810+n)

    def test_nine_states_inherit_full_prior_evidence(self):
        result=verify_base_pair_guest(self.paths)
        self.assertEqual(result["captured_real_frames"],9)
        self.assertEqual(result["pairs_per_window"],32)
        self.assertEqual(result["active_median_difference_us"],60)
        self.assertTrue(result["in_guest_private_pixel_parity_verified"])
        self.assertFalse(result["physical_switch_tested"])
        self.assertFalse(result["whole_game_speedup_proven"])

    def test_missing_parity_proof(self):
        mark(self.paths[1],status=(255,48,48))
        with self.assertRaises(ValueError):
            verify_base_pair_guest(self.paths)

    def test_saturated_bar(self):
        mark(self.paths[1],cached=65535)
        with self.assertRaises(ValueError):
            verify_base_pair_guest(self.paths)

    def test_corrupted_bit(self):
        with Image.open(self.paths[1]) as original:
            image=original.convert("RGB")
        draw=ImageDraw.Draw(image)
        x=sample_x(PAIR_X[0]+4*6)
        draw.rectangle((x-1,12,x+1,18),fill=(255,0,0))
        image.save(self.paths[1])
        with self.assertRaises(ValueError):
            verify_base_pair_guest(self.paths)

    def test_old_terrain_or_cache_proof_mandatory(self):
        with Image.open(self.paths[4]) as original:
            image=original.convert("RGB")
        draw=ImageDraw.Draw(image)
        x=sample_x(948+4*10)
        draw.rectangle((x-1,12,x+1,18),fill=(13,14,15))
        image.save(self.paths[4])
        with self.assertRaises(ValueError):
            verify_base_pair_guest(self.paths)

    def test_wrong_frame_count(self):
        with self.assertRaises(ValueError):
            verify_base_pair_guest(self.paths[:-1])

if __name__=="__main__":
    unittest.main()
