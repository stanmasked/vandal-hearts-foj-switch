"""Stage249 negative optical tests; no fabricated speedup assumptions."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage249_stability_guest_check import (
    COLD_X,WARM_X,SPREAD_X,STATUS_X,ON_COLORS,OFF,READY,
    verify_stability_guest,
)
from test_stage246_phase_guest_check import frame
from test_stage248_base_pair_guest_check import mark as stage248_mark

def paint(path:Path,cold=7000,warm=510,spread=230,status=READY):
    with Image.open(path) as original:
        image=original.convert("RGB")
    d=ImageDraw.Draw(image)
    for origin,color,value in zip(
        (COLD_X,WARM_X,SPREAD_X),ON_COLORS,(cold,warm,spread)
    ):
        for bit in range(16):
            x=sample_x(origin+bit*4)
            d.rectangle((x-1,12,x+1,18),fill=color if value&(1<<bit) else OFF)
    x=sample_x(STATUS_X+4)
    d.rectangle((x-4,12,x+4,18),fill=status)
    image.save(path)

class Stage249StabilityGuestTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.paths=tuple(Path(folder.name)/(state+".png") for state in STATES)
        for index,(state,path) in enumerate(zip(STATES,self.paths)):
            frame(path,index,state)
            stage248_mark(path,750+index,810+index)
            paint(path,cold=7000+index,warm=510+index,spread=230+index)

    def test_nine_valid_guest_receipts_and_prior_proofs(self):
        report=verify_stability_guest(self.paths)
        self.assertEqual(report["real_game_state_screenshots"],9)
        self.assertEqual(report["complete_paired_windows_per_scene_at_least"],3)
        self.assertEqual(report["active_median_base_cold_refill_us"],7004)
        self.assertFalse(report["gpu_time_or_fps_measured"])

    def test_zero_spread_is_valid_without_claiming_no_clock_drift(self):
        paint(self.paths[0],spread=0)
        self.assertEqual(verify_stability_guest(self.paths)["states"]["initial"][
            "largest_32_pair_window_spread_us"],0)

    def test_pending_not_three_windows_rejected(self):
        paint(self.paths[2],status=(81,140,178))
        with self.assertRaises(ValueError):
            verify_stability_guest(self.paths)

    def test_missing_cold_or_warm_value_rejected(self):
        paint(self.paths[3],cold=0)
        with self.assertRaises(ValueError):
            verify_stability_guest(self.paths)
        paint(self.paths[3],cold=7000,warm=0)
        with self.assertRaises(ValueError):
            verify_stability_guest(self.paths)

    def test_saturated_spread_rejected(self):
        paint(self.paths[4],spread=65535)
        with self.assertRaises(ValueError):
            verify_stability_guest(self.paths)

    def test_corrupt_bit_rejected(self):
        with Image.open(self.paths[5]) as original:
            image=original.convert("RGB")
        d=ImageDraw.Draw(image)
        x=sample_x(WARM_X+4*10)
        d.rectangle((x-1,12,x+1,18),fill=(255,0,0))
        image.save(self.paths[5])
        with self.assertRaises(ValueError):
            verify_stability_guest(self.paths)

    def test_prior_stage248_proof_cannot_be_bypassed(self):
        with Image.open(self.paths[6]) as original:
            image=original.convert("RGB")
        d=ImageDraw.Draw(image)
        x=sample_x(780+4*6)
        d.rectangle((x-1,12,x+1,18),fill=(255,0,0))
        image.save(self.paths[6])
        with self.assertRaises(ValueError):
            verify_stability_guest(self.paths)

    def test_missing_image_rejected(self):
        with self.assertRaises(ValueError):
            verify_stability_guest(self.paths[:-1])

if __name__=="__main__":
    unittest.main()
