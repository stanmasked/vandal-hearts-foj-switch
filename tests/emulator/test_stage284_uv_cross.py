"""Stage284 synthetic regressions; mock PNGs are not GPU proof."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
from tools.foj_stage274_pass_contract_check import expected_receipt
from tools.foj_stage280_shifted_boundary_sd import target_rgb
from tools.foj_stage284_uv_cross_sd import (
    SCHEMA, CASE, WIDTH, SPLIT_U, SPLIT_V, U_EXPECTED_X, V_EXPECTED_Y,
    U_PROFILE_ROWS, U_PROFILE_X, V_PROFILE_COLUMNS, V_PROFILE_Y,
    CAPTURE_VIEWPORT_HEIGHT, CAPTURE_VIEWPORT_PROBE_X, CONTROL_POSITIONS,
    expected_at, near_atlas,
)
from tools.foj_stage284_uv_cross_check import verify


def mock_files(root: Path) -> None:
    folder = root / CASE
    folder.mkdir(parents=True)
    baseline = generated_dds((*VIOLET, 128))
    masked = near_atlas()
    digest = hashlib.sha256(masked).hexdigest()
    meta = {
        "schema": SCHEMA, "scenario": CASE, "changed_file": "material0.dds",
        "generated_only": True, "original_ps3_resources": False,
        "actual_gpu_render_verified": False,
        "near_original_dds_sha256": hashlib.sha256(baseline).hexdigest(),
        "near_dds_sha256": digest,
        "near_alpha_split_u": SPLIT_U, "near_alpha_split_v": SPLIT_V,
        "expected_half_transition_x": U_EXPECTED_X,
        "expected_half_transition_y": V_EXPECTED_Y,
        "near_texture_dimensions": [WIDTH, WIDTH],
        "u_profile_rows": list(U_PROFILE_ROWS),
        "u_profile_x_positions": list(U_PROFILE_X),
        "v_profile_columns": list(V_PROFILE_COLUMNS),
        "v_profile_y_positions": list(V_PROFILE_Y),
        "capture_viewport_height": CAPTURE_VIEWPORT_HEIGHT,
        "capture_viewport_probe_x": CAPTURE_VIEWPORT_PROBE_X,
        "control_probe_positions": {k: list(v) for k, v in CONTROL_POSITIONS.items()},
        "expected_native_pass_order": [2, 1, 0],
        "expected_probe_rgb": {k: list(expected_at(k)) for k in CONTROL_POSITIONS},
        "profile_goal": "verify orthogonal U and V alpha edges simultaneously in one generated DDS without assuming sampler filtering",
    }
    (folder / "generated-input.json").write_text(json.dumps(meta))
    for phase in ("before", "after"):
        (folder / f"near-dds-{phase}.sha256").write_text(digest + "\n")
    (folder / "native-sort-pass.txt").write_bytes(b"FOJ_NATIVE_SORT_V1 2,1,0\n")
    (folder / "native-alpha-pass.txt").write_bytes(expected_receipt("original"))
    (folder / "guest.log").write_text("PIL unit fixture only; not a NeXium guest\n")
    for frame_name, bg in (
            ("gpu-initial.png", (112, 145, 110)),
            ("gpu-later.png", (54, 31, 59))):
        image = Image.new("RGB", (1280, 720), bg)
        for y in U_PROFILE_ROWS:
            for x in U_PROFILE_X:
                image.putpixel((x, y), target_rgb(0 if x < U_EXPECTED_X else 255))
        for x in V_PROFILE_COLUMNS:
            for y in V_PROFILE_Y:
                image.putpixel((x, y), target_rgb(0 if y < V_EXPECTED_Y else 255))
        draw = ImageDraw.Draw(image)
        for name, (cx, cy) in CONTROL_POSITIONS.items():
            draw.rectangle((cx - 4, cy - 4, cx + 4, cy + 4), fill=expected_at(name))
        draw.rectangle((0, CAPTURE_VIEWPORT_HEIGHT, 1279, 719), fill=(14, 18, 24))
        image.save(folder / frame_name)


class OrthogonalUVAlphaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        mock_files(self.root)
        self.folder = self.root / CASE

    def tearDown(self):
        self.temp.cleanup()

    def _mutate_image(self, frame, fn):
        path = self.folder / frame
        with Image.open(path) as source:
            image = source.convert("RGB")
        fn(image)
        image.save(path)

    def test_dds_changes_only_alpha_and_records_both_axes(self):
        baseline = generated_dds((*VIOLET, 128))
        masked = near_atlas()
        self.assertEqual(masked[:128], baseline[:128])
        self.assertEqual(sum(a != b for a, b in zip(masked, baseline)), WIDTH * WIDTH)
        self.assertTrue(all(
            masked[i] == baseline[i]
            for i in range(128, len(masked)) if (i - 128) % 4 != 3
        ))
        meta = json.loads((self.folder / "generated-input.json").read_text())
        self.assertEqual(meta["near_alpha_split_u"], 46)
        self.assertEqual(meta["near_alpha_split_v"], 46)
        self.assertEqual(meta["expected_half_transition_x"], 649)
        self.assertEqual(meta["expected_half_transition_y"], 395)

    def test_both_uv_edges_verified_in_same_texture_without_sampler_inference(self):
        receipt = verify(self.root)
        self.assertEqual(receipt["schema"], "foj.stage284.real_native_orthogonal_uv_alpha_edges.v1")
        self.assertEqual(receipt["profile_sample_count"], 324)
        self.assertEqual(receipt["sampler_filter_mode"], "NOT_INFERRED")
        self.assertTrue(receipt["generated_only"])
        self.assertFalse(receipt["original_ps3_resources"])
        self.assertEqual(
            [receipt["initial"]["u_profiles"][str(y)]["half_transition"]
             for y in U_PROFILE_ROWS], [649, 649, 649])
        self.assertEqual(
            [receipt["initial"]["v_profiles"][str(x)]["half_transition"]
             for x in V_PROFILE_COLUMNS], [395, 395, 395])

    def test_capture_viewport_scale_mismatch_rejected(self):
        self._mutate_image("gpu-initial.png",
                           lambda im: im.putpixel((CAPTURE_VIEWPORT_PROBE_X, 600), (1, 2, 3)))
        with self.assertRaisesRegex(ValueError, "viewport scale"):
            verify(self.root)

    def test_missing_u_edge_rejected(self):
        def mutate(im):
            for y in U_PROFILE_ROWS:
                for x in U_PROFILE_X:
                    im.putpixel((x, y), target_rgb(255))
        self._mutate_image("gpu-initial.png", mutate)
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_wrong_v_edge_position_rejected(self):
        def mutate(im):
            for x in V_PROFILE_COLUMNS:
                for y in V_PROFILE_Y:
                    im.putpixel((x, y), target_rgb(0 if y < 400 else 255))
        self._mutate_image("gpu-initial.png", mutate)
        with self.assertRaisesRegex(ValueError, "V crossing"):
            verify(self.root)

    def test_impossible_rgb_rejected_off_curve(self):
        self._mutate_image("gpu-initial.png",
                           lambda im: im.putpixel((U_EXPECTED_X, 440), (0, 0, 0)))
        with self.assertRaisesRegex(ValueError, "off source-over curve"):
            verify(self.root)

    def test_nonmonotone_u_edge_rejected(self):
        self._mutate_image("gpu-initial.png",
                           lambda im: im.putpixel((655, 440), target_rgb(0)))
        with self.assertRaisesRegex(ValueError, "nonmonotone U"):
            verify(self.root)

    def test_native_sort_receipt_mismatch_rejected(self):
        (self.folder / "native-sort-pass.txt").write_text("FOJ_NATIVE_SORT_V1 0,1,2\n")
        with self.assertRaisesRegex(ValueError, "sort receipt"):
            verify(self.root)

    def test_source_digest_mutation_rejected(self):
        (self.folder / "near-dds-after.sha256").write_text("0" * 64 + "\n")
        with self.assertRaisesRegex(ValueError, "DDS identity"):
            verify(self.root)

    def test_duplicate_frame_rejected(self):
        (self.folder / "gpu-later.png").write_bytes((self.folder / "gpu-initial.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "duplicate framebuffer"):
            verify(self.root)

    def test_temporal_material_mutation_rejected(self):
        self._mutate_image("gpu-later.png",
                           lambda im: im.putpixel((650, 440), target_rgb(0)))
        with self.assertRaisesRegex(ValueError, "profiles changed"):
            verify(self.root)

    def test_missing_v_edge_rejected(self):
        def mutate(im):
            for x in V_PROFILE_COLUMNS:
                for y in V_PROFILE_Y:
                    im.putpixel((x, y), target_rgb(0))
        self._mutate_image("gpu-initial.png", mutate)
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_native_alpha_receipt_mismatch_rejected(self):
        (self.folder / "native-alpha-pass.txt").write_text("FOJ_NATIVE_ALPHA_PASS_V1 bad\n")
        with self.assertRaisesRegex(ValueError, "alpha/blend/depth"):
            verify(self.root)


if __name__ == "__main__":
    unittest.main()
