"""Stage255 synthetic optical mutation tests with Stage254 ancestry."""
from __future__ import annotations
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage255_budget_guest_check import (
    verify_budget_guest,ORIGIN,STEP,STATUS_X,ON,OFF,READY)
from test_stage254_reuse_guest_check import BoundedReuseGuestTests,paint254

def paint255(path:Path,values=(384,48,48,192,192,16),status=READY):
    with Image.open(path) as source:
        im=source.convert("RGB")
    d=ImageDraw.Draw(im)
    for i,(number,color) in enumerate(zip(values,ON)):
        for bit in range(16):
            x=sample_x(ORIGIN+i*STEP+bit*4)
            d.rectangle((x-1,105,x+1,112),
                        fill=color if number&(1<<bit) else OFF)
    x=sample_x(STATUS_X+4)
    d.rectangle((x-4,105,x+4,112),fill=status)
    im.save(path)

class BudgetGuestTests(unittest.TestCase):
    def setUp(self):
        BoundedReuseGuestTests.setUp(self)
        for path in self.paths:
            paint255(path)
    def tearDown(self):
        BoundedReuseGuestTests.tearDown(self)
    def test_nine_frames_and_ancestral_proofs(self):
        report=verify_budget_guest(self.paths)
        self.assertEqual(report["actual_battle_states"],9)
        self.assertEqual(report["tight_budget_allocations"],48)
        self.assertEqual(report["low_resolution_fallback_blocks"],16)
        self.assertEqual(report["stage254_unchanged_allocations"],32)
        self.assertFalse(report["physical_nintendo_switch_tested"])
    def test_wrong_frame_count_rejected(self):
        paint255(self.paths[0],values=(383,48,48,192,192,16))
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_wrong_allocations_rejected(self):
        paint255(self.paths[1],values=(384,47,48,192,192,16))
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_wrong_releases_rejected(self):
        paint255(self.paths[2],values=(384,48,47,192,192,16))
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_wrong_hits_rejected(self):
        paint255(self.paths[3],values=(384,48,48,193,192,16))
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_wrong_misses_rejected(self):
        paint255(self.paths[4],values=(384,48,48,192,191,16))
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_wrong_fallback_count_rejected(self):
        paint255(self.paths[5],values=(384,48,48,192,192,15))
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_false_ready_rejected(self):
        paint255(self.paths[6],status=(0,0,0))
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_stage254_ancestor_required(self):
        paint254(self.paths[7],values=(384,48,33,32,16,675))
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_corrupt_bit_rejected(self):
        with Image.open(self.paths[8]) as source:
            im=source.convert("RGB")
        x=sample_x(ORIGIN+STEP*5+4*8)
        ImageDraw.Draw(im).rectangle((x-1,105,x+1,112),fill=(255,0,0))
        im.save(self.paths[8])
        with self.assertRaises(ValueError):verify_budget_guest(self.paths)
    def test_reject_incomplete_state_set(self):
        with self.assertRaises(ValueError):verify_budget_guest(self.paths[:-1])

if __name__=="__main__":unittest.main()
