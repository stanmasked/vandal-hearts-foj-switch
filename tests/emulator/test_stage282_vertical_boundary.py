"""Stage282 synthetic-only regression tests. Mock images are NEVER GPU proof."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
from tools.foj_stage280_shifted_boundary_sd import target_rgb
from tools.foj_stage282_vertical_boundary_sd import (
    SCHEMA, CASES, SPLITS, WIDTH, COLUMNS, EXPECTED_Y,
    PROBE_X, near_atlas, expected_at, positions, profile_y,
    NATIVE_EXPECTED_Y, NATIVE_FRAME_HEIGHT, CAPTURE_VIEWPORT_HEIGHT,
    CAPTURE_VIEWPORT_PROBE_X,
)
from tools.foj_stage282_vertical_boundary_check import inspect, verify


def mock_files(root: Path) -> None:
    source = generated_dds((*VIOLET, 128))
    original = hashlib.sha256(source).hexdigest()
    for case in CASES:
        folder = root / case
        folder.mkdir()
        digest = hashlib.sha256(near_atlas(case)).hexdigest()
        meta = {
            "schema": SCHEMA, "scenario": case,
            "changed_file": "material0.dds",
            "generated_only": True, "original_ps3_resources": False,
            "actual_gpu_render_verified": False,
            "near_dds_sha256": digest,
            "near_original_dds_sha256": original,
            "near_alpha_split_y": SPLITS[case],
            "expected_half_transition_y": EXPECTED_Y[case],
            "native_expected_half_transition_y": NATIVE_EXPECTED_Y[case],
            "native_framebuffer_height": NATIVE_FRAME_HEIGHT,
            "capture_viewport_height": CAPTURE_VIEWPORT_HEIGHT,
            "capture_viewport_probe_x": CAPTURE_VIEWPORT_PROBE_X,
            "capture_scale_y": round(CAPTURE_VIEWPORT_HEIGHT / NATIVE_FRAME_HEIGHT, 8),
            "near_texture_dimensions": [WIDTH, WIDTH],
            "profile_x_columns": list(COLUMNS),
            "profile_y_positions": list(profile_y(case)),
            "probe_x": PROBE_X,
            "expected_native_pass_order": [2, 1, 0],
            "expected_probe_rgb": {
                k: list(expected_at(case, k)) for k in positions(case)},
            "profile_goal": "verify V-driven displacement without assuming GPU filtering",
        }
        (folder / "generated-input.json").write_text(json.dumps(meta))
        for phase in ("before", "after"):
            (folder / f"near-dds-{phase}.sha256").write_text(digest + "\n")
        (folder / "native-sort-pass.txt").write_bytes(
            b"FOJ_NATIVE_SORT_V1 2,1,0\n")
        (folder / "native-alpha-pass.txt").write_bytes(
            b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0\n")
        (folder / "guest.log").write_text(
            "generated PIL unit fixture, never NeXium\n")
        for frame_name, bg in (
                ("gpu-initial.png", (112, 145, 110)),
                ("gpu-later.png", (54, 31, 59))):
            image = Image.new("RGB", (1280, 720), bg)
            draw = ImageDraw.Draw(image)
            for label, (x, y) in positions(case).items():
                draw.rectangle((x - 5, y - 5, x + 5, y + 5),
                               fill=expected_at(case, label))
            for x in COLUMNS:
                for y in profile_y(case):
                    image.putpixel(
                        (x, y), target_rgb(
                            0 if y < EXPECTED_Y[case] else 255))
            draw.rectangle((0, CAPTURE_VIEWPORT_HEIGHT, 1279, 719),
                           fill=(42, 42, 50))
            image.save(folder / frame_name)


def mutate(root: Path, case: str, frame: str, x: int, y: int,
           rgb: tuple[int, int, int]) -> None:
    path = root / case / frame
    with Image.open(path) as source:
        image = source.convert("RGB")
    image.putpixel((x, y), rgb)
    image.save(path)


class Stage282VerticalBoundaryTests(unittest.TestCase):
    def test_dds_vertical_split_changes_only_alpha_and_header_is_unchanged(self):
        source = generated_dds((*VIOLET, 128))
        for case in CASES:
            with self.subTest(case=case):
                data = near_atlas(case)
                self.assertEqual(len(data), 16512)
                self.assertEqual(data[:128], source[:128])
                for y in range(WIDTH):
                    for x in range(WIDTH):
                        offset = 128 + 4 * (y * WIDTH + x)
                        self.assertEqual(data[offset:offset+3],
                                         source[offset:offset+3])
                        self.assertEqual(data[offset+3],
                                         0 if y < SPLITS[case] else 255)

    def test_expected_rows_match_frozen_native_c11_projection(self):
        # foj_gpu_prepare_stream uses scale=.84*min(width,height)/extent;
        # at 1280x720 with extent=2 this maps y to framebuffer Y using .84.
        top = (1.0 - .84 * .69) * 360.0
        bottom = (1.0 - .84 * (-.50)) * 360.0
        self.assertAlmostEqual(top, 151.344)
        self.assertAlmostEqual(bottom, 511.2)
        scale_y = CAPTURE_VIEWPORT_HEIGHT / NATIVE_FRAME_HEIGHT
        for case in CASES:
            with self.subTest(case=case):
                projected_native = top + (bottom - top) * SPLITS[case] / 64.0
                self.assertAlmostEqual(projected_native, NATIVE_EXPECTED_Y[case])
                projected_capture = projected_native * scale_y
                self.assertEqual(round(projected_capture), EXPECTED_Y[case])

    def test_324_synthetic_rgb_samples_accepted_without_sampler_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_files(root)
            receipt = verify(root)
            self.assertEqual(receipt["profile_sample_count"], 324)
            self.assertEqual(receipt["sampler_filter_mode"], "NOT_INFERRED")
            self.assertFalse(receipt["physical_switch_verified"])
            for x in COLUMNS:
                crossings = [
                    receipt["cases"][case]["initial"]["columns"][str(x)]
                           ["half_transition_y"] for case in CASES]
                self.assertEqual(crossings,
                                 [EXPECTED_Y[case] for case in CASES])
                self.assertEqual(crossings[1] - crossings[0], 65)

    def test_capture_viewport_scale_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_files(root)
            path = root / CASES[0] / "gpu-initial.png"
            with Image.open(path) as source:
                image = source.convert("RGB")
            # Move the first non-background row down by one pixel. The
            # auditor must not silently use a stale capture-to-frame scale.
            image.putpixel((CAPTURE_VIEWPORT_PROBE_X, CAPTURE_VIEWPORT_HEIGHT),
                           image.getpixel((CAPTURE_VIEWPORT_PROBE_X, 0)))
            image.save(path)
            with self.assertRaisesRegex(ValueError, "capture viewport scaling"):
                inspect(path, CASES[0])

    def test_gradual_physically_possible_alpha_edge_is_allowed(self):
        from tools.foj_stage280_shifted_boundary_check import (
            REFERENCE_CLEAR, DELTA,
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_files(root)
            for case in CASES:
                center = EXPECTED_Y[case]
                for name in ("gpu-initial.png", "gpu-later.png"):
                    path = root / case / name
                    with Image.open(path) as source:
                        img = source.convert("RGB")
                    for x in COLUMNS:
                        for y in range(center-2, center+3):
                            alpha = (y-(center-3)) / 6.0
                            img.putpixel((x, y), tuple(
                                round(REFERENCE_CLEAR[i] + alpha * DELTA[i])
                                for i in range(3)))
                    img.save(path)
            result = verify(root)
            self.assertGreater(
                result["cases"][CASES[0]]["initial"]["columns"]
                      [str(COLUMNS[0])]["intermediate_sample_count"], 0)

    def test_impossible_black_pixel_rejected_off_curve(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            mutate(root, CASES[0], "gpu-initial.png",
                   COLUMNS[0], EXPECTED_Y[CASES[0]]+2, (0, 0, 0))
            with self.assertRaisesRegex(ValueError, "off-curve RGB"):
                verify(root)

    def test_white_pixel_rejected_outside_envelope(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            mutate(root, CASES[0], "gpu-initial.png",
                   COLUMNS[0], EXPECTED_Y[CASES[0]]+2, (255, 255, 255))
            with self.assertRaisesRegex(ValueError, "out-of-envelope"):
                verify(root)

    def test_wrong_axis_position_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            case = CASES[0]
            for name in ("gpu-initial.png", "gpu-later.png"):
                path = root / case / name
                with Image.open(path) as source:
                    image = source.convert("RGB")
                for x in COLUMNS:
                    for y in profile_y(case):
                        image.putpixel((x, y), target_rgb(
                            0 if y < EXPECTED_Y[case] + 8 else 255))
                image.save(path)
            with self.assertRaises(ValueError):
                verify(root)

    def test_nonmonotone_vertical_profile_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            case = CASES[0]
            mutate(root, case, "gpu-initial.png",
                   COLUMNS[0], EXPECTED_Y[case]-7, target_rgb(255))
            with self.assertRaisesRegex(ValueError, "nonmonotone"):
                verify(root)

    def test_native_receipt_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            (root / CASES[0] / "native-sort-pass.txt").write_text(
                "FOJ_NATIVE_SORT_V1 0,1,2\n")
            with self.assertRaisesRegex(ValueError, "native GPU draw/pass"):
                verify(root)

    def test_source_alpha_digest_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            (root / CASES[1] / "near-dds-after.sha256").write_text(
                "0"*64 + "\n")
            with self.assertRaisesRegex(ValueError, "DDS mutated"):
                verify(root)

    def test_duplicate_frame_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            folder = root / CASES[0]
            (folder / "gpu-later.png").write_bytes(
                (folder / "gpu-initial.png").read_bytes())
            with self.assertRaisesRegex(ValueError, "duplicate framebuffer"):
                verify(root)

    def test_column_specific_corruption_is_not_hidden_by_center_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            case = CASES[1]
            mutate(root, case, "gpu-initial.png", COLUMNS[2],
                   EXPECTED_Y[case]+2, (0, 0, 0))
            with self.assertRaisesRegex(ValueError, "off-curve RGB"):
                verify(root)

    def test_temporal_material_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); mock_files(root)
            case = CASES[0]
            mutate(root, case, "gpu-later.png", COLUMNS[0],
                   EXPECTED_Y[case], target_rgb(0))
            with self.assertRaisesRegex(ValueError, "changed between frames"):
                verify(root)


if __name__ == "__main__":
    unittest.main()
