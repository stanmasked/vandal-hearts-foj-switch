"""Stage254 900-KiB bounded reuse optical mutation and ancestry tests."""
from __future__ import annotations
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage254_reuse_guest_check import (
    verify_reuse_guest,ORIGIN,STEP,STATUS_X,ON,OFF,READY
)
from test_stage253_churn_guest_check import ChurnGuestTests,paint253

def paint254(path:Path,values=(384,48,32,32,16,675),status=READY):
    with Image.open(path) as source:
        im=source.convert("RGB")
    d=ImageDraw.Draw(im)
    for i,(number,color) in enumerate(zip(values,ON)):
        for bit in range(16):
            x=sample_x(ORIGIN+i*STEP+bit*4)
            d.rectangle((x-1,89,x+1,96),
                        fill=color if number&(1<<bit) else OFF)
    x=sample_x(STATUS_X+4)
    d.rectangle((x-4,89,x+4,96),fill=status)
    im.save(path)

class BoundedReuseGuestTests(unittest.TestCase):
    def setUp(self):
        ChurnGuestTests.setUp(self)
        for path in self.paths:
            paint254(path)
    def test_nine_frames_and_inherited_parity(self):
        r=verify_reuse_guest(self.paths)
        self.assertEqual(r["actual_battle_states"],9)
        self.assertEqual(r["exact_policy_allocations"],48)
        self.assertEqual(r["bounded_reuse_allocations"],32)
        self.assertEqual(r["additional_capacity_at_320x180_kib"],675)
        self.assertFalse(r["allocator_fragmentation_or_rss_measured"])
    def test_wrong_exact_rejected(self):
        paint254(self.paths[0],values=(384,47,32,32,16,675))
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths)
    def test_wrong_reuse_rejected(self):
        paint254(self.paths[1],values=(384,48,33,32,16,675))
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths)
    def test_mismatched_releases_rejected(self):
        paint254(self.paths[2],values=(384,48,32,31,16,675))
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths)
    def test_mismatched_savings_rejected(self):
        paint254(self.paths[3],values=(384,48,32,32,17,675))
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths)
    def test_mismatched_capacity_rejected(self):
        paint254(self.paths[4],values=(384,48,32,32,16,674))
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths)
    def test_bad_status_rejected(self):
        paint254(self.paths[5],status=(0,0,0))
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths)
    def test_bad_bit_color_rejected(self):
        with Image.open(self.paths[6]) as source:im=source.convert("RGB")
        x=sample_x(ORIGIN+5*STEP+4*8)
        ImageDraw.Draw(im).rectangle((x-1,89,x+1,96),fill=(255,0,0))
        im.save(self.paths[6])
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths)
    def test_stage253_ancestor_required(self):
        paint253(self.paths[7],values=(384,48,47,192,192,3600))
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths)
    def test_only_nine_states(self):
        with self.assertRaises(ValueError):verify_reuse_guest(self.paths[:-1])

if __name__=="__main__":unittest.main()
