"""Stage238 fail-closed synthetic screenshot controls for real NeXium checker."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from tools.foj_stage231_threat_guest_check import BACKGROUND, HERO, ENEMY, SIZE
from tools.foj_stage238_cache_guest_check import (
    STATES, IDLE, FIRST, SECOND, OVERFLOW, HIT, NO_HIT,
    EXPECTED_GENERATIONS, EXPECTED_HITS, verify_cache_screenshots,
)


def make_frame(path: Path, generation: tuple[int,int,int], hit: tuple[int,int,int],
               *, blank=False, wrong_size=False) -> None:
    if wrong_size:
        Image.new("RGB", (960, 600), BACKGROUND).save(path)
        return
    image = Image.new("RGB", SIZE, (0, 0, 0) if blank else BACKGROUND)
    if not blank:
        draw=ImageDraw.Draw(image)
        draw.rectangle((580,210,609,239), fill=HERO)
        draw.rectangle((780,310,809,339), fill=ENEMY)
        draw.rectangle((256,12,263,19), fill=generation)
        draw.rectangle((268,12,275,19), fill=hit)
    image.save(path)


class CacheGuestProofTests(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.frames = tuple(Path(root.name) / (state + ".png")
                            for state in STATES)
        self.reset()

    def reset(self):
        for path, generation, hit in zip(
            self.frames, EXPECTED_GENERATIONS, EXPECTED_HITS):
            make_frame(path, generation, hit)

    def test_valid_nine_frame_sequence(self):
        report=verify_cache_screenshots(self.frames)
        self.assertTrue(report["post_guard_hover_reuses_second_matrix"])
        self.assertFalse(report["fps_gain_measured"])

    def test_recomputation_while_hovering_rejected(self):
        make_frame(self.frames[2], SECOND, HIT)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_visibility_toggle_forces_recalculation_rejected(self):
        make_frame(self.frames[3], SECOND, HIT)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_missed_guard_invalidation_rejected(self):
        make_frame(self.frames[6], FIRST, HIT)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_unexpected_extra_calculation_rejected(self):
        make_frame(self.frames[7], OVERFLOW, HIT)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_cancelled_marker_leak_rejected(self):
        make_frame(self.frames[5], FIRST, HIT)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_stale_marker_after_y_rejected(self):
        make_frame(self.frames[8], SECOND, HIT)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_no_actual_cache_hit_rejected(self):
        make_frame(self.frames[2], FIRST, NO_HIT)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_blank_guest_rejected(self):
        make_frame(self.frames[1], FIRST, HIT, blank=True)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_wrong_frame_size_rejected(self):
        make_frame(self.frames[1], FIRST, HIT, wrong_size=True)
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames)

    def test_wrong_number_of_frames_rejected(self):
        with self.assertRaises(ValueError):
            verify_cache_screenshots(self.frames[:-1])


if __name__ == "__main__":
    unittest.main()
