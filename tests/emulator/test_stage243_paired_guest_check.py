"""Stage243: fail-closed ABBA guest pairing, pixel parity and timer controls."""
from __future__ import annotations

import copy
import hashlib
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage238_cache_guest_check import STATES
from tools.foj_stage243_paired_guest_check import (
    ORDER, ROLES, SCHEMA, summarize, MODE_X, MODE_Y, MODE_CACHED,
    MODE_UNCACHED, verify_mode_tile,
)


def digest(x):
    return hashlib.sha256(str(x).encode()).hexdigest()


def sample_results():
    results={}
    for i,(name,role) in enumerate(zip(ORDER,ROLES)):
        results[name] = {
            "role": role,
            "nro_sha256": digest(role),
            "nexium_sha256": digest("NeXium nightly"),
            "scene_sha256": {state:digest("scene:"+state) for state in STATES},
            "frame_sha256": {state:digest(name+"-"+state) for state in STATES},
            "render_us": {state:(
                (8100 if role == "cached" else 9400)
                + i * 11 + j * 7)
                for j,state in enumerate(STATES)},
        }
    return results


class ModeTileScreenshotTests(unittest.TestCase):
    def guest_frame(self, cached: bool) -> Image.Image:
        frame = Image.new("RGB", (1280,720), (13,19,33))
        draw = ImageDraw.Draw(frame)
        # Derived from 36 genuine NeXium PNGs in Actions 39281551213:
        # A/B mode tile covers GUI x515..519 and y12..18.
        draw.rectangle((515,12,519,18),
                       fill=MODE_CACHED if cached else MODE_UNCACHED)
        return frame

    def test_cached_tile_at_real_guest_coordinate(self):
        verify_mode_tile(self.guest_frame(True), "cached", "initial")

    def test_uncached_tile_at_real_guest_coordinate(self):
        verify_mode_tile(self.guest_frame(False), "uncached", "initial")

    def test_opposite_mode_rejected(self):
        with self.assertRaises(ValueError):
            verify_mode_tile(self.guest_frame(True), "uncached", "initial")

    def test_old_wrong_x520_fails_not_rerouted_to_background(self):
        frame = self.guest_frame(True)
        self.assertEqual(frame.getpixel((520,15)), (13,19,33))
        self.assertIn(517, MODE_X)
        self.assertNotIn(520, MODE_X)

    def test_corrupted_one_of_nine_samples_rejected(self):
        frame = self.guest_frame(False)
        frame.putpixel((MODE_X[1],MODE_Y[1]),(13,19,33))
        with self.assertRaises(ValueError):
            verify_mode_tile(frame, "uncached", "guarded")


class PairedGuestControls(unittest.TestCase):
    def assert_rejected(self, mutate):
        data=sample_results()
        mutate(data)
        with self.assertRaises(ValueError):
            summarize(data)

    def test_valid_abba_and_no_fps_claim(self):
        receipt=summarize(sample_results())
        self.assertEqual(receipt["schema"], SCHEMA)
        self.assertEqual(receipt["independent_guest_processes"],4)
        self.assertEqual(receipt["real_guest_screenshots"],36)
        self.assertTrue(receipt["scene_pixels_identical_except_top_diagnostics"])
        self.assertFalse(receipt["switch_fps_measured"])
        self.assertGreater(
            receipt["pair_results"]["hovered"]["uncached_minus_cached_us"],0)

    def test_real_slowdown_is_not_failed_by_speed_gate(self):
        data=sample_results()
        for name in ("uncached_first","uncached_second"):
            data[name]["render_us"] = {s:100+i for i,s in enumerate(STATES)}
        report=summarize(data)
        self.assertLess(report["pair_results"]["hovered"]["uncached_minus_cached_us"],0)
        self.assertFalse(report["hard_speedup_threshold_enforced"])

    def test_missing_guest_rejected(self):
        self.assert_rejected(lambda x:x.pop("cached_second"))

    def test_fifth_guest_rejected(self):
        self.assert_rejected(lambda x:x.update(extra=copy.deepcopy(x["cached_first"])))

    def test_reversed_experiment_order_rejected(self):
        self.assert_rejected(lambda x:x["cached_first"].update(role="uncached"))

    def test_duplicate_cached_experimental_nro_rejected(self):
        self.assert_rejected(lambda x:x["uncached_first"].update(
            nro_sha256=x["cached_first"]["nro_sha256"]))

    def test_cached_build_changed_rejected(self):
        self.assert_rejected(lambda x:x["cached_second"].update(
            nro_sha256=digest("changed cached build")))

    def test_emulator_changed_rejected(self):
        self.assert_rejected(lambda x:x["uncached_second"].update(
            nexium_sha256=digest("changed emulator")))

    def test_different_battle_scene_rejected(self):
        self.assert_rejected(lambda x:x["uncached_first"]["scene_sha256"].update(
            selected=digest("shifted cursor/gameplay")))

    def test_duplicate_guest_capture_rejected(self):
        self.assert_rejected(lambda x:x["uncached_second"].update(
            frame_sha256=copy.deepcopy(x["uncached_first"]["frame_sha256"])))

    def test_missing_scene_timing_rejected(self):
        self.assert_rejected(lambda x:x["cached_first"]["render_us"].pop("guarded"))

    def test_zero_timing_rejected(self):
        self.assert_rejected(lambda x:x["cached_first"]["render_us"].update(
            hovered=0))

    def test_boolean_timing_rejected(self):
        self.assert_rejected(lambda x:x["uncached_first"]["render_us"].update(
            hovered=True))

    def test_saturated_timing_rejected(self):
        self.assert_rejected(lambda x:x["uncached_first"]["render_us"].update(
            hovered=65535))


if __name__=="__main__":
    unittest.main()
