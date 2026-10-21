"""Stage285 regressions; synthetic PNGs are never GPU evidence."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from test_stage284_uv_cross import mock_files
from tools.foj_stage280_shifted_boundary_sd import target_rgb
from tools.foj_stage284_uv_cross_sd import CASE, U_EXPECTED_X, V_EXPECTED_Y
from tools.foj_stage285_uv_cross_intersection_check import verify


class UVIntersectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        mock_files(self.root)
        self.folder = self.root / CASE
        self._paint_expected_grid("gpu-initial.png", U_EXPECTED_X, V_EXPECTED_Y)
        self._paint_expected_grid("gpu-later.png", U_EXPECTED_X, V_EXPECTED_Y)

    def tearDown(self):
        self.temp.cleanup()

    def _mutate(self, frame, fn):
        path = self.folder / frame
        with Image.open(path) as source:
            image = source.convert("RGB")
        fn(image)
        image.save(path)

    def _paint_expected_grid(self, frame, split_x, split_y):
        path = self.folder / frame
        with Image.open(path) as source:
            image = source.convert("RGB")
        for y in range(V_EXPECTED_Y - 8, V_EXPECTED_Y + 9):
            for x in range(U_EXPECTED_X - 8, U_EXPECTED_X + 9):
                rgb = target_rgb(255 if x >= split_x and y >= split_y else 0)
                image.putpixel((x, y), rgb)
        image.save(path)

    def test_both_real_frame_contracts_cover_all_289_intersection_samples(self):
        receipt = verify(self.root)
        self.assertEqual(receipt["schema"], "foj.stage285.real_native_uv_cross_intersection.v1")
        self.assertEqual(receipt["grid_dimensions"], [17, 17])
        self.assertEqual(receipt["samples_per_frame"], 289)
        self.assertEqual(receipt["total_samples"], 578)
        self.assertEqual(receipt["crossing_x"], 649)
        self.assertEqual(receipt["crossing_y"], 395)
        self.assertEqual(
            receipt["frames"][0]["quadrant_sample_counts"],
            {"northwest_clear": 64, "northeast_clear": 72,
             "southwest_clear": 72, "southeast_opaque": 81},
        )
        self.assertEqual(
            receipt["frames"][0]["grid_sha256"],
            receipt["frames"][1]["grid_sha256"],
        )
        self.assertTrue(receipt["generated_only"])
        self.assertFalse(receipt["original_ps3_resources"])

    def test_one_channel_rgb_rounding_noise_is_accepted(self):
        # The real NeXium frame differs from the integer blend target by one
        # channel value at clear pixels; geometry and quadrant classification
        # must remain strict while this harmless rounding difference is allowed.
        self._mutate("gpu-initial.png",
                     lambda image: image.putpixel((641, 387), (126, 129, 123)))
        receipt = verify(self.root)
        self.assertEqual(receipt["frames"][0]["max_channel_delta"], 1)
        self.assertEqual(receipt["frames"][0]["rgb_channel_tolerance"], 2)

    def test_opaque_pixel_leaking_into_northeast_quadrant_rejected(self):
        self._mutate("gpu-initial.png",
                     lambda image: image.putpixel((650, 394), target_rgb(255)))
        with self.assertRaisesRegex(ValueError, r"intersection mismatch at \(650,394\)"):
            verify(self.root)

    def test_missing_opaque_corner_at_intersection_rejected(self):
        self._mutate("gpu-later.png",
                     lambda image: image.putpixel((649, 395), target_rgb(0)))
        with self.assertRaisesRegex(ValueError, r"intersection mismatch at \(649,395\)"):
            verify(self.root)

    def test_one_pixel_u_boundary_shift_rejected(self):
        self._paint_expected_grid("gpu-initial.png", U_EXPECTED_X + 1, V_EXPECTED_Y)
        with self.assertRaisesRegex(ValueError, r"intersection mismatch at \(649,395\)"):
            verify(self.root)

    def test_patch_cannot_change_between_two_guest_frames(self):
        # Preserve valid expected colors but mutate one frame's cross patch;
        # the checker rejects the bad pixel rather than trusting frame identity.
        self._mutate("gpu-later.png",
                     lambda image: image.putpixel((649, 395), target_rgb(0)))
        with self.assertRaisesRegex(ValueError, "intersection mismatch"):
            verify(self.root)

    def test_original_resources_cannot_be_claimed_by_synthetic_fixture(self):
        path = self.folder / "generated-input.json"
        meta = json.loads(path.read_text())
        meta["original_ps3_resources"] = True
        path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, "provenance mismatch"):
            verify(self.root)


if __name__ == "__main__":
    unittest.main()
