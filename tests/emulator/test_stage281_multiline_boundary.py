"""Stage281 host-only regressions; generated PNGs are never real GPU evidence."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from test_stage280_shifted_boundary import mock_files
from tools.foj_stage280_shifted_boundary_sd import (
    CASES, FRAME_CROSSINGS, PROFILE_Y, profile_x, target_rgb,
)
from tools.foj_stage281_multiline_boundary_check import (
    ROWS, inspect_rows, verify,
)


def mock_multiline(root: Path) -> None:
    mock_files(root)
    for case in CASES:
        for name in ("gpu-initial.png", "gpu-later.png"):
            path = root / case / name
            with Image.open(path) as source:
                img = source.convert("RGB")
            for y in ROWS:
                for x in profile_x(case):
                    img.putpixel((x, y),
                                 target_rgb(0 if x < FRAME_CROSSINGS[case] else 255))
            img.save(path)


class Stage281MultilineTests(unittest.TestCase):
    def test_five_rows_both_cases_pass_in_synthetic_unit_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            audit = verify(root)
            self.assertEqual(audit["row_count_per_frame"], 5)
            self.assertFalse(audit["physical_switch_verified"])
            self.assertEqual(audit["rows"], list(ROWS))
            for y in ROWS:
                measured = [
                    audit["cases"][case][str(y)]["crossing_x"] for case in CASES
                ]
                self.assertEqual(measured,
                                 [FRAME_CROSSINGS[case] for case in CASES])
                self.assertEqual(measured[1] - measured[0], 62)

    def test_only_one_row_wrong_position_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            case = CASES[0]
            for name in ("gpu-initial.png", "gpu-later.png"):
                path = root / case / name
                with Image.open(path) as src:
                    img = src.convert("RGB")
                for x in profile_x(case):
                    img.putpixel((x, 438),
                                 target_rgb(0 if x < FRAME_CROSSINGS[case] + 8 else 255))
                img.save(path)
            with self.assertRaisesRegex(ValueError, "wrong UV edge position"):
                verify(root)

    def test_missing_secondary_row_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            case = CASES[0]
            for name in ("gpu-initial.png", "gpu-later.png"):
                path = root / case / name
                with Image.open(path) as src:
                    img = src.convert("RGB")
                for x in profile_x(case):
                    img.putpixel((x, 436), (112, 145, 110))
                img.save(path)
            with self.assertRaises(ValueError):
                verify(root)

    def test_off_curve_pixel_in_secondary_row_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            case = CASES[1]
            path = root / case / "gpu-initial.png"
            with Image.open(path) as src:
                img = src.convert("RGB")
            img.putpixel((FRAME_CROSSINGS[case] + 2, 444), (0, 0, 0))
            img.save(path)
            with self.assertRaisesRegex(ValueError, "off-curve RGB"):
                verify(root)

    def test_secondary_row_nonmonotone_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            case = CASES[0]
            path = root / case / "gpu-initial.png"
            with Image.open(path) as src:
                img = src.convert("RGB")
            img.putpixel((FRAME_CROSSINGS[case] - 7, 438), target_rgb(255))
            img.save(path)
            with self.assertRaisesRegex(ValueError, "nonmonotone"):
                verify(root)

    def test_noncentral_row_changes_between_frames_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            case = CASES[0]
            path = root / case / "gpu-later.png"
            with Image.open(path) as src:
                img = src.convert("RGB")
            img.putpixel((FRAME_CROSSINGS[case], 442), target_rgb(0))
            img.save(path)
            with self.assertRaisesRegex(ValueError, "not stable"):
                verify(root)

    def test_inherited_stage280_dds_digest_guard_still_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            (root / CASES[0] / "near-dds-after.sha256").write_text(
                "0" * 64 + "\n"
            )
            with self.assertRaisesRegex(ValueError, "identity changed"):
                verify(root)

    def test_inherited_native_receipt_guard_still_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            (root / CASES[1] / "native-sort-pass.txt").write_text(
                "FOJ_NATIVE_SORT_V1 0,1,2\n"
            )
            with self.assertRaisesRegex(ValueError, "native GPU descriptor"):
                verify(root)

    def test_inherited_duplicate_png_guard_still_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            folder = root / CASES[0]
            (folder / "gpu-later.png").write_bytes(
                (folder / "gpu-initial.png").read_bytes()
            )
            with self.assertRaisesRegex(ValueError, "duplicate framebuffer"):
                verify(root)

    def test_original_middle_row_is_reconciled_with_stage280(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mock_multiline(root)
            for case in CASES:
                frame = root / case / "gpu-initial.png"
                self.assertEqual(
                    inspect_rows(frame, case)[str(PROFILE_Y)]["crossing_x"],
                    FRAME_CROSSINGS[case],
                )


if __name__ == "__main__":
    unittest.main()
