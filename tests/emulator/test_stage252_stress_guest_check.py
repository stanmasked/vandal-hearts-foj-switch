"""Stage252 NeXium negative tests for endurance optical and inherited receipts."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage252_stress_guest_check import (
    verify_stress_guest,ORIGIN,STEP,COLORS,OFF,STATUS_X,READY
)
from test_stage251_compact_guest_check import (
    frame,stage248_mark,stage249_paint,stage250_paint,
    paint as stage251_paint
)

def paint(path:Path,values=(96,8,96,3600),status=READY):
    with Image.open(path) as source: im=source.convert("RGB")
    d=ImageDraw.Draw(im)
    for i,(value,on) in enumerate(zip(values,COLORS)):
        for bit in range(16):
            x=sample_x(ORIGIN+i*STEP+4*bit)
            d.rectangle((x-1,60,x+1,66),
                        fill=on if value&(1<<bit) else OFF)
    x=sample_x(STATUS_X+4)
    d.rectangle((x-4,60,x+4,66),fill=status)
    im.save(path)

class Stage252StressTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.paths=tuple(Path(t.name)/(state+".png") for state in STATES)
        for i,(state,path) in enumerate(zip(STATES,self.paths)):
            frame(path,i,state)
            stage248_mark(path,750+i,810+i)
            stage249_paint(path,cold=7000+i,warm=510+i,spread=230+i)
            stage250_paint(path,
                tuple(x+i for x in (1000,4000,9000)),
                tuple(x+i for x in (90,350,820)))
            stage251_paint(path)
            paint(path)
    def test_real_nine_state_inherited_receipts(self):
        result=verify_stress_guest(self.paths)
        self.assertEqual(result["genuine_battle_states"],9)
        self.assertEqual(result["matched_releases"],96)
        self.assertEqual(result["simulated_allocation_failures"],8)
        self.assertFalse(result["whole_game_improvement_proven"])
    def test_cycle_corruption_rejected(self):
        paint(self.paths[0],values=(95,8,96,3600))
        with self.assertRaises(ValueError):verify_stress_guest(self.paths)
    def test_fault_count_corruption_rejected(self):
        paint(self.paths[1],values=(96,7,96,3600))
        with self.assertRaises(ValueError):verify_stress_guest(self.paths)
    def test_allocations_corruption_rejected(self):
        paint(self.paths[2],values=(96,8,95,3600))
        with self.assertRaises(ValueError):verify_stress_guest(self.paths)
    def test_peak_corruption_rejected(self):
        paint(self.paths[3],values=(96,8,96,3599))
        with self.assertRaises(ValueError):verify_stress_guest(self.paths)
    def test_bad_readiness_rejected(self):
        paint(self.paths[4],status=(0,0,0))
        with self.assertRaises(ValueError):verify_stress_guest(self.paths)
    def test_invalid_bit_colour_rejected(self):
        with Image.open(self.paths[5]) as src: im=src.convert("RGB")
        x=sample_x(ORIGIN+2*STEP+4*7)
        ImageDraw.Draw(im).rectangle((x-1,60,x+1,66),fill=(255,0,0))
        im.save(self.paths[5])
        with self.assertRaises(ValueError):verify_stress_guest(self.paths)
    def test_ancestor_stage251_is_mandatory(self):
        stage251_paint(self.paths[6],values=(225,900,3599))
        with self.assertRaises(ValueError):verify_stress_guest(self.paths)
    def test_frame_count_rejected(self):
        with self.assertRaises(ValueError):verify_stress_guest(self.paths[:-1])

if __name__=="__main__":unittest.main()
