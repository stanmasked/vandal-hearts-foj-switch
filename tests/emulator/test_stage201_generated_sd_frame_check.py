"""Stage 201 screenshot validator fail-closed fixtures: ALL pixels invented."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw
from tools.foj_stage201_nexium_sd_actor_frame_check import (
    STATES, SCHEMA, verify
)

SOURCE=(233,182,87)
ACCEPT=(0,136,255)
YELLOW=(255,255,0)
WIRE=(218,228,189)
WIDTH,HEIGHT=1280,720


def populate(folder:Path, *, freeze=False, rejected=False,
             fade_absent=False, missing_marker=False):
    phases={
        "initial":0,"step-025":1,"still-025":1,"reset":0,
        "fade-0":0,"fade-25":2,"fade-50":3,"fade-75":4,
        "fade-done":5,"reset-after":0,
    }
    for name in STATES:
        phase=0 if freeze else phases[name]
        img=Image.new("RGB",(WIDTH,HEIGHT),(37,28,24))
        draw=ImageDraw.Draw(img)
        if not missing_marker:
            draw.rectangle((1232,12,1265,35),fill=SOURCE)
        draw.rectangle(
            (1196,12,1227,35),
            fill=(255,0,0) if rejected else ACCEPT
        )
        if name in ("fade-0","fade-25","fade-50","fade-75") and (
            not fade_absent):
            draw.rectangle((1160,12,1191,35),fill=YELLOW)
        # Draw an articulated invented figure with rigid torso & changing
        # elbow/leg positions, well away from all status indicators.
        dx=42*phase
        draw.line((580,210,620+dx,310,640-dx,410,590+dx,520),
                  fill=WIRE,width=3)
        draw.line((600,390,540-dx,530,660+dx,570),
                  fill=WIRE,width=3)
        img.save(folder/f"rig-{name}.png")


class Stage201FrameCheck(unittest.TestCase):
    def test_all_ten_generated_guest_states_detected(self):
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path)
            populate(folder)
            report=verify(folder)
            self.assertEqual(report["schema"],SCHEMA)
            self.assertEqual(report["frames_verified"],10)
            self.assertTrue(report["generated_secondary_asset_accepted"])
            self.assertGreater(report["initial_motion_changed_pixels"],65)
            self.assertEqual(report["paused_stillness_changed_pixels"],0)
            self.assertEqual(report["reset_changed_pixels"],0)
            self.assertEqual(report["initial_crossfade_zero_changed_pixels"],0)
            self.assertEqual(report["after_final_reset_changed_pixels"],0)
            self.assertFalse(report["actual_original_ps3_model_loaded"])

    def test_static_guest_does_not_pass_as_moving(self):
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path)
            populate(folder,freeze=True)
            with self.assertRaisesRegex(ValueError,"did not advance"):
                verify(folder)

    def test_missing_sd_marker_is_detected(self):
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path)
            populate(folder,missing_marker=True)
            with self.assertRaisesRegex(ValueError,"marker absent"):
                verify(folder)

    def test_bad_secondary_clip_marker_is_detected(self):
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path)
            populate(folder,rejected=True)
            with self.assertRaisesRegex(ValueError,"not accepted"):
                verify(folder)

    def test_missing_fade_marker_rejected(self):
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path)
            populate(folder,fade_absent=True)
            with self.assertRaisesRegex(ValueError,"not shown"):
                verify(folder)

    def test_missing_guest_frame_rejected(self):
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path)
            populate(folder)
            (folder/"rig-fade-50.png").unlink()
            with self.assertRaises((OSError,ValueError)):
                verify(folder)


if __name__=="__main__":
    unittest.main()
