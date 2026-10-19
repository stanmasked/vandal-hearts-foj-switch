"""Stage244: synthetic positive and adversarial screenshot decoder controls."""
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
from tools.foj_stage244_paired_guest_check import (
    SAMPLED,INACTIVE,CACHED_X,UNCACHED_X,STATUS_X,BIT_Y,
    ON_CACHED,ON_UNCACHED,PENDING,READY,FAILED,
    validate_guest_pair_screenshots,
)


def make_frame(path:Path,state:str,n:int,*,wrong_tile:bool=False,
               corrupted_bit:bool=False,zero:bool=False) -> None:
    canvas=Image.new("RGB",SIZE,BACKGROUND)
    draw=ImageDraw.Draw(canvas)
    draw.rectangle((580,210,609,239),fill=HERO)
    draw.rectangle((780,310,809,339),fill=ENEMY)
    draw.rectangle((409,12,415,18),fill=EXPECTED_GENERATIONS[n])
    draw.rectangle((420,12,427,18),fill=EXPECTED_HITS[n])
    for bit,x in enumerate(BIT_X):
        draw.rectangle((x-1,12,x+1,18),
                       fill=ON if (8000+n*23)&(1<<bit) else OFF)
    if state in SAMPLED:
        for xs,v,on in ((CACHED_X,0 if zero else 400+n,ON_CACHED),
                        (UNCACHED_X,5000+n,ON_UNCACHED)):
            for bit,x in enumerate(xs):
                draw.rectangle((x-1,12,x+1,18),
                               fill=on if v&(1<<bit) else OFF)
        draw.rectangle((STATUS_X[0]-1,12,STATUS_X[-1]+1,18),
                       fill=FAILED if wrong_tile else READY)
        if corrupted_bit:
            x=CACHED_X[5]
            draw.rectangle((x-1,12,x+1,18),fill=(250,0,10))
    else:
        draw.rectangle((STATUS_X[0]-1,12,STATUS_X[-1]+1,18),fill=PENDING)
    canvas.save(path)


class InProcessPairGuestTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.paths=tuple(Path(tmp.name)/(s+".png") for s in STATES)
        self.write_frames()

    def write_frames(self,**changes):
        for i,(p,s) in enumerate(zip(self.paths,STATES)):
            make_frame(p,s,i,**changes.get(s,{}))

    def test_realistic_guest_game_sequence(self):
        result=validate_guest_pair_screenshots(self.paths)
        self.assertEqual(result["real_guest_screenshots"],9)
        self.assertEqual(result["independent_guest_processes"],1)
        self.assertEqual(len(result["guest_scene_values_ns"]),5)
        self.assertFalse(result["switch_fps_measured"])
        self.assertEqual(
            result["guest_scene_values_ns"]["selected"]["cached_warm_ns_per_call"],
            401)
        self.assertEqual(
            result["guest_scene_values_ns"]["selected"]["uncached_ns_per_call"],
            5001)

    def test_wrong_parity_status_rejected(self):
        self.write_frames(selected={"wrong_tile":True})
        with self.assertRaises(ValueError):
            validate_guest_pair_screenshots(self.paths)

    def test_corrupt_single_timing_bit_rejected(self):
        self.write_frames(hovered={"corrupted_bit":True})
        with self.assertRaises(ValueError):
            validate_guest_pair_screenshots(self.paths)

    def test_zero_guest_time_rejected(self):
        self.write_frames(guarded={"zero":True})
        with self.assertRaises(ValueError):
            validate_guest_pair_screenshots(self.paths)

    def test_missing_one_genuine_frame_rejected(self):
        with self.assertRaises(ValueError):
            validate_guest_pair_screenshots(self.paths[:-1])

    def test_corrupted_game_state_rejected(self):
        self.paths[4].unlink()
        with self.assertRaises(FileNotFoundError):
            validate_guest_pair_screenshots(self.paths)

    def test_inactive_guest_must_not_measure(self):
        with Image.open(self.paths[0]) as frame:
            im=frame.convert("RGB")
        draw=ImageDraw.Draw(im)
        draw.rectangle((STATUS_X[0]-1,12,STATUS_X[-1]+1,18),fill=READY)
        im.save(self.paths[0])
        with self.assertRaises(ValueError):
            validate_guest_pair_screenshots(self.paths)


if __name__ == "__main__":
    unittest.main()
