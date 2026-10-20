"""Stage253 optical smoke and negative mutations, with Stage252 ancestry."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage253_churn_guest_check import (
    verify_churn_guest,ORIGIN,STEP,ON,OFF,READY,STATUS_X
)
from test_stage251_compact_guest_check import (
    frame,stage248_mark,stage249_paint,stage250_paint,
    paint as paint251
)
from test_stage252_stress_guest_check import paint as paint252

def paint253(path:Path,values=(384,48,48,192,192,3600),status=READY):
    with Image.open(path) as src: im=src.convert("RGB")
    d=ImageDraw.Draw(im)
    for i,(value,on) in enumerate(zip(values,ON)):
        for bit in range(16):
            x=sample_x(ORIGIN+i*STEP+4*bit)
            d.rectangle((x-1,76,x+1,82),
                        fill=on if value&(1<<bit) else OFF)
    x=sample_x(STATUS_X+4)
    d.rectangle((x-4,76,x+4,82),fill=status)
    im.save(path)

class ChurnGuestTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.paths=tuple(Path(tmp.name)/(s+".png") for s in STATES)
        for i,(state,path) in enumerate(zip(STATES,self.paths)):
            frame(path,i,state)
            stage248_mark(path,750+i,810+i)
            stage249_paint(path,cold=7000+i,warm=510+i,spread=230+i)
            stage250_paint(path,tuple(x+i for x in (1000,4000,9000)),
                                tuple(x+i for x in (90,350,820)))
            paint251(path)
            paint252(path)
            paint253(path)
    def test_valid_nine_screens(self):
        data=verify_churn_guest(self.paths)
        self.assertEqual(data["test_frames_in_single_guest"],384)
        self.assertEqual(data["allocations"],48)
        self.assertEqual(data["releases"],48)
        self.assertEqual(data["hits"],192)
        self.assertFalse(data["allocator_heap_fragmentation_measured"])
    def test_wrong_allocations_rejected(self):
        paint253(self.paths[0],values=(384,47,48,192,192,3600))
        with self.assertRaises(ValueError):verify_churn_guest(self.paths)
    def test_wrong_releases_rejected(self):
        paint253(self.paths[1],values=(384,48,47,192,192,3600))
        with self.assertRaises(ValueError):verify_churn_guest(self.paths)
    def test_wrong_cache_hits_rejected(self):
        paint253(self.paths[2],values=(384,48,48,191,192,3600))
        with self.assertRaises(ValueError):verify_churn_guest(self.paths)
    def test_peak_overflow_rejected(self):
        paint253(self.paths[3],values=(384,48,48,192,192,65535))
        with self.assertRaises(ValueError):verify_churn_guest(self.paths)
    def test_bad_status_rejected(self):
        paint253(self.paths[4],status=(0,0,0))
        with self.assertRaises(ValueError):verify_churn_guest(self.paths)
    def test_invalid_color_rejected(self):
        with Image.open(self.paths[5]) as src:im=src.convert("RGB")
        x=sample_x(ORIGIN+2*STEP+4*8)
        ImageDraw.Draw(im).rectangle((x-1,76,x+1,82),fill=(255,0,0))
        im.save(self.paths[5])
        with self.assertRaises(ValueError):verify_churn_guest(self.paths)
    def test_stage252_ancestor_required(self):
        paint252(self.paths[6],values=(96,7,96,3600))
        with self.assertRaises(ValueError):verify_churn_guest(self.paths)
    def test_missing_screen_rejected(self):
        with self.assertRaises(ValueError):verify_churn_guest(self.paths[:-1])

if __name__=="__main__":unittest.main()
