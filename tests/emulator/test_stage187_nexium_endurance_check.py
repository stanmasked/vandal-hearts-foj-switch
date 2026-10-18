"""Generated-only classifier regressions; not emulator execution evidence."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from tools.foj_stage187_nexium_endurance_check import (
    CHECKPOINTS, SCHEMA, verify_endurance
)


class TestStage187Endurance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        heat = Image.new("RGB", (1280, 720), (17, 22, 34))
        iso = Image.new("RGB", (1280, 720), (16, 22, 35))
        for picture, fill, cursor in (
            (heat, (51, 101, 160), (255, 232, 140)),
            (iso, (165, 115, 77), (255, 224, 118)),
        ):
            painter = ImageDraw.Draw(picture)
            painter.rectangle((130, 120, 810, 560), fill=fill)
            painter.rectangle((1235, 16, 1261, 34), fill=(231, 94, 86))
            painter.rectangle((625, 340, 654, 370), fill=cursor)
        heat.save(self.directory / "ref-coll-heat.png")
        iso.save(self.directory / "ref-coll-iso.png")
        for count in CHECKPOINTS:
            image = iso if count % 2 else heat
            image.save(self.directory / f"coll-endurance-{count:02d}.png")
        self.write_rss()

    def tearDown(self):
        self.temp.cleanup()

    def write_rss(self, extra=0, non_monotonic=False):
        content = []
        for idx, count in enumerate(CHECKPOINTS):
            timestamp = 100000 + idx * 3
            if non_monotonic and idx == 3:
                timestamp -= 20
            rss = 280000 + idx * 1500 + (extra if idx == 8 else 0)
            content.append(f"{count}\t{rss}\t{timestamp}\n")
        (self.directory / "nexium-host-rss.tsv").write_text(
            "".join(content), encoding="utf-8")

    def verify(self):
        return verify_endurance(self.directory)

    def test_nine_genuine_shaped_frames_but_no_hardware_claim(self):
        report = self.verify()
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["button_press_release_events"], 48)
        self.assertEqual(report["checkpoint_count"], 9)
        self.assertTrue(report["host_memory_measurement_not_guest_memory"])
        self.assertFalse(report["physical_switch_execution_verified"])
        self.assertFalse(report["original_foj_gameplay_verified"])
        self.assertNotIn(str(self.directory), str(report))

    def test_black_window_rejected(self):
        Image.new("RGB", (1280, 720), (0, 0, 0)).save(
            self.directory / "coll-endurance-24.png")
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_mode_transition_rejected(self):
        shutil.copyfile(self.directory / "coll-endurance-00.png",
                        self.directory / "coll-endurance-01.png")
        with self.assertRaises(ValueError):
            self.verify()

    def test_frame_drift_in_long_run_rejected(self):
        frame = Image.open(self.directory / "coll-endurance-48.png")
        ImageDraw.Draw(frame).rectangle(
            (130, 120, 810, 560), fill=(200, 30, 31))
        frame.save(self.directory / "coll-endurance-48.png")
        with self.assertRaises(ValueError):
            self.verify()

    def test_incomplete_host_rss_samples_rejected(self):
        path = self.directory / "nexium-host-rss.tsv"
        path.write_text(path.read_text().splitlines()[0] + "\n")
        with self.assertRaises(ValueError):
            self.verify()

    def test_fast_fake_rss_sequence_rejected(self):
        rows = (self.directory / "nexium-host-rss.tsv").read_text().splitlines()
        (self.directory / "nexium-host-rss.tsv").write_text(
            "\n".join("\t".join(row.split("\t")[:2] + ["1000"]) for row in rows))
        with self.assertRaises(ValueError):
            self.verify()

    def test_extreme_host_rss_growth_rejected(self):
        self.write_rss(extra=600 * 1024)
        with self.assertRaises(ValueError):
            self.verify()

    def test_missing_guest_checkpoint_rejected(self):
        (self.directory / "coll-endurance-25.png").unlink()
        with self.assertRaises((ValueError, OSError)):
            self.verify()


if __name__ == "__main__":
    unittest.main()
