"""Stage251 optical KiB verifier rejects tampering and missing older proofs."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage246_phase_guest_check import sample_x
from tools.foj_stage251_compact_guest_check import (
    BASE_X,ON,OFF,READY,STATUS_X,verify_compact_guest,
)
from test_stage246_phase_guest_check import frame
from test_stage248_base_pair_guest_check import mark as stage248_mark
from test_stage249_stability_guest_check import paint as stage249_paint
from test_stage250_scale_guest_check import paint as stage250_paint

def paint(path:Path,values=(225,900,3600),status=READY):
    with Image.open(path) as src: im=src.convert("RGB")
    d=ImageDraw.Draw(im)
    for i,(value,color) in enumerate(zip(values,ON)):
        for bit in range(16):
            x=sample_x(BASE_X+i*72+bit*4)
            d.rectangle((x-1,44,x+1,50),
                        fill=color if value&(1<<bit) else OFF)
    x=sample_x(STATUS_X+4)
    d.rectangle((x-4,44,x+4,50),fill=status)
    im.save(path)

class CompactGuestTests(unittest.TestCase):
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
            paint(path)
    def test_nine_states_and_inherited_proofs(self):
        receipt=verify_compact_guest(self.paths)
        self.assertEqual(receipt["actual_states"],9)
        self.assertEqual(receipt["pixel_payload_bytes_for_three_sizes"],
                         [230400,921600,3686400])
        self.assertEqual(receipt["memory_scaling_for_smallest_state_pct"],93.75)
        self.assertFalse(receipt["heap_allocator_overhead_or_rss_measured"])
        self.assertFalse(receipt["whole_game_speedup_proven"])
    def test_wrong_capacity_fails(self):
        paint(self.paths[1],values=(225,900,3599))
        with self.assertRaises(ValueError):
            verify_compact_guest(self.paths)
    def test_zero_capacity_fails(self):
        paint(self.paths[2],values=(0,900,3600))
        with self.assertRaises(ValueError):
            verify_compact_guest(self.paths)
    def test_saturation_fails(self):
        paint(self.paths[3],values=(225,65535,3600))
        with self.assertRaises(ValueError):
            verify_compact_guest(self.paths)
    def test_missing_ready_tile_fails(self):
        paint(self.paths[4],status=(0,0,0))
        with self.assertRaises(ValueError):
            verify_compact_guest(self.paths)
    def test_invalid_kiB_bit_fails(self):
        with Image.open(self.paths[5]) as src: im=src.convert("RGB")
        x=sample_x(BASE_X+2*72+4*7)
        ImageDraw.Draw(im).rectangle((x-1,44,x+1,50),fill=(255,0,0))
        im.save(self.paths[5])
        with self.assertRaises(ValueError):
            verify_compact_guest(self.paths)
    def test_inherited_stage250_is_mandatory(self):
        with Image.open(self.paths[6]) as src: im=src.convert("RGB")
        x=sample_x(536+4*7)
        ImageDraw.Draw(im).rectangle((x-1,28,x+1,34),fill=(255,0,0))
        im.save(self.paths[6])
        with self.assertRaises(ValueError):
            verify_compact_guest(self.paths)
    def test_wrong_frame_count_fails(self):
        with self.assertRaises(ValueError):
            verify_compact_guest(self.paths[:-1])

if __name__=="__main__":unittest.main()
