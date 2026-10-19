"""Stage247: reject stale, missing or forged guest cache-hit tiles."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage246_phase_guest_check import sample_x, X
from tools.foj_stage247_base_cache_guest_check import (
    HIT_RGB, MISS_RGB, TILE_X, classify_cache_tile, verify_base_cache_guest,
)
from test_stage246_phase_guest_check import frame

def paint(path: Path, color) -> None:
    with Image.open(path) as original:
        image = original.convert("RGB")
    draw = ImageDraw.Draw(image)
    left = sample_x(TILE_X+1)
    right = sample_x(TILE_X+7)
    draw.rectangle((left,12,right,18),fill=color)
    image.save(path)

class Stage247CacheGuestChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.paths = tuple(Path(temp.name) / (s+".png") for s in STATES)
        for idx,(state,path) in enumerate(zip(STATES,self.paths)):
            frame(path,idx,state)
            paint(path,HIT_RGB)

    def test_all_nine_cache_proofs_and_old_schemas(self):
        report = verify_base_cache_guest(self.paths)
        self.assertEqual(report["authentic_screenshot_count"],9)
        self.assertEqual(report["warm_base_cache_proofs"],9)
        self.assertEqual(report["scene_states"]["selected"]["terrain_mean_us"],6117)
        self.assertFalse(report["actual_game_speedup_proven"])
        self.assertFalse(report["physical_switch_tested"])

    def test_one_red_cold_miss_rejected(self):
        paint(self.paths[4],MISS_RGB)
        self.assertFalse(classify_cache_tile(Image.open(self.paths[4])))
        with self.assertRaises(ValueError):
            verify_base_cache_guest(self.paths)

    def test_uncalibrated_unknown_tile_rejected(self):
        paint(self.paths[2],(123,4,91))
        with self.assertRaises(ValueError):
            verify_base_cache_guest(self.paths)

    def test_missing_frame_rejected(self):
        with self.assertRaises(ValueError):
            verify_base_cache_guest(self.paths[:-1])

    def test_existing_four_phase_proof_cannot_be_bypassed(self):
        with Image.open(self.paths[1]) as original:
            image = original.convert("RGB")
        draw=ImageDraw.Draw(image)
        x=sample_x(X[0]+4*10)
        draw.rectangle((x-1,12,x+1,18),fill=(0,0,0))
        image.save(self.paths[1])
        with self.assertRaises(ValueError):
            verify_base_cache_guest(self.paths)

if __name__ == "__main__":
    unittest.main()
