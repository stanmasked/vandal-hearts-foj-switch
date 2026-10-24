from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

from tools.foj_stage340_fixture import create, fixture_bytes
from tools.foj_stage341_generated_diagnose import diagnose, invert_generated_rgb
from tools.foj_stage341_nexium_display import SETTINGS, install as install_display, verify as verify_display
from tools.foj_stage341_frame_gate import (
    DDS_BYTES, EVIDENCE_FILES, FRAME_HEIGHT, FRAME_WIDTH, MARKER,
    MARKER_NAME, SAMPLE_X, SAMPLE_Y, SCHEMA, _sample_uv, audit_frames,
    decode_bgra8_dds,
)


def render_reference(dds: bytes) -> Image.Image:
    rgba = decode_bgra8_dds(dds)
    image = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), (11, 17, 23))
    px = image.load()
    for y in range(FRAME_HEIGHT):
        for x in range(FRAME_WIDTH):
            # Test helper renders the expected quad, but production code never
            # imports this helper and never paints a screenshot on the host.
            u = ((x + 0.5) / FRAME_WIDTH - 0.1) / 0.8
            v = ((y + 0.5) / FRAME_HEIGHT - 0.1) / 0.8
            if 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0:
                tx = min(255, max(0, int(u * 256)))
                ty = min(255, max(0, int(v * 256)))
                off = (ty * 256 + tx) * 4
                px[x, y] = tuple(rgba[off:off + 3])
    return image


class Stage341FrameGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sd = self.root / "sdmc"
        self.gpu = self.sd / "switch" / "foj" / "gpu"
        self.gpu.mkdir(parents=True)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.source = self.gpu / "source.dds"
        create(self.source)
        (self.gpu / "foj_actor.vert.dksh").write_bytes(b"generated vertex DKSH")
        (self.gpu / "foj_triangle.frag.dksh").write_bytes(b"generated fragment DKSH")
        (self.gpu / MARKER_NAME).write_bytes(MARKER)
        self.frames = (render_reference(self.source.read_bytes()),)
        first = render_reference(self.source.read_bytes())
        later = first.copy()
        later.putpixel((2, 2), (250, 240, 230))
        first.save(self.evidence / "gpu-initial.png")
        later.save(self.evidence / "gpu-later.png")
        (self.evidence / "guest.log").write_text("synthetic test log\n", encoding="utf-8")
        (self.evidence / "nexium-archive.sha256").write_text(
            "a" * 64 + "  nexium-linux-x86_64.tar.gz\n", encoding="ascii"
        )
        summary = {
            "schema": "foj.stage340.generated_bgra8_dds_fixture.v1",
            "generated_only": True,
            "original_ps3_assets_used": False,
            "physical_switch_verified": False,
            "width": 256, "height": 256, "format": "BGRA8",
            "dds_file_bytes": DDS_BYTES,
            "sha256": __import__("hashlib").sha256(self.source.read_bytes()).hexdigest(),
        }
        (self.evidence / "generated-source.json").write_text(
            json.dumps(summary, sort_keys=True), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_nro_wires_external_source_to_native_upload_and_quad_draw(self):
        main = (Path(__file__).resolve().parents[2] / "gpu" / "deko3d_clear_main.c").read_text()
        self.assertIn("FOJ_GPU_STAGE341_PRIVATE_DDS_DRAW", main)
        self.assertIn('sdmc:/switch/foj/gpu/source.dds', main)
        self.assertIn("foj_stage332_dds_inspect", main)
        self.assertIn("foj_stage332_dds_decode", main)
        self.assertIn("inspected.format!=FOJ_STAGE332_BGRA8", main)
        self.assertIn("foj_stage336_native_record_rgba_upload", main)
        self.assertIn("FojGpuVertex stage341_quad[6]", main)
        self.assertIn("sampler.minFilter=DkFilter_Nearest", main)
        self.assertIn("FOJ_STAGE341_PRIVATE_DDS_TEXTURE_SAMPLE_V1", main)
        self.assertIn("dkQueuePresentImage(queue,swapchain,slot);", main)
        self.assertNotIn("FOJ_GPU_STAGE329_PATCH_STREAM=1", main)

    def test_public_workflow_never_uploads_raw_frames_or_private_inputs(self):
        workflow = (Path(__file__).resolve().parents[2] /
                    ".github" / "workflows" / "stage341-private-dds-frame.yml").read_text()
        self.assertIn("tools.foj_stage340_fixture create", workflow)
        self.assertIn("foj-stage341-generated-only-frame-aggregate", workflow)
        self.assertIn("path: runtime-evidence-public/", workflow)
        self.assertNotIn("FoJ_Stage340_Selected_Original_DDS", workflow)
        self.assertNotIn("Google Drive", workflow)
        self.assertNotIn("path: runtime-evidence/", workflow)

    def test_owner_local_runner_requires_runtime_assets_outside_checkout(self):
        runner = (Path(__file__).resolve().parents[2] /
                  "tools" / "foj_stage341_private_run.py").read_text()
        self.assertIn("under(nexium.resolve(), REPO_ROOT)", runner)
        self.assertIn("under(shader_dir.resolve(), REPO_ROOT)", runner)
        self.assertIn("under(library_path.resolve(), REPO_ROOT)", runner)
        self.assertIn("under(icd.resolve(), REPO_ROOT)", runner)

    def test_capture_runners_support_imagemagick_6_and_7(self):
        root = Path(__file__).resolve().parents[2]
        private_runner = (root / "tools" / "foj_stage341_private_run.py").read_text()
        public_runner = (root / "tools" / "foj_stage341_nexium_drive.sh").read_text()
        self.assertIn('shutil.which("magick")', private_runner)
        self.assertIn('[magick_bin, "import", "-window"', private_runner)
        self.assertIn("capture_cmd=(magick import)", public_runner)

    def test_capture_runners_wait_for_distinct_rendered_frames(self):
        root = Path(__file__).resolve().parents[2]
        private_runner = (root / "tools" / "foj_stage341_private_run.py").read_text()
        public_runner = (root / "tools" / "foj_stage341_nexium_drive.sh").read_text()
        self.assertIn("ImageChops.difference", private_runner)
        self.assertIn("could not capture a distinct presented frame", private_runner)
        self.assertIn("ImageChops.difference", public_runner)
        self.assertIn("could not capture a distinct presented frame", public_runner)
        self.assertIn("gpu-later-candidate.png", private_runner)


    def test_isolated_nexium_display_matches_full_frame_and_is_fail_closed(self):
        isolated = self.root / "nexium-profile"
        isolated.mkdir(mode=0o700)
        path = install_display(isolated)
        self.assertEqual(verify_display(isolated), path)
        self.assertEqual(json.loads(path.read_text()), SETTINGS)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(SETTINGS["game_bar"])
        self.assertEqual(SETTINGS["aspect"], "Letterbox")
        self.assertEqual(SETTINGS["filter"], "Nearest")
        with self.assertRaises(FileExistsError):
            install_display(isolated)
        path.write_text('{"log_level":"Info","game_bar":true}', encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_display(isolated)
        path.unlink()
        path.symlink_to(self.source)
        with self.assertRaises(ValueError):
            verify_display(isolated)

    def test_both_stage341_runners_request_isolated_full_display(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/stage341-private-dds-frame.yml").read_text()
        private = (root / "tools/foj_stage341_private_run.py").read_text()
        self.assertIn("tools.foj_stage341_nexium_display install", workflow)
        self.assertIn("install_display(data_root)", private)
        self.assertIn("tools/foj_stage341_nexium_display.py", workflow)
        self.assertNotIn("path: $NEXIUM_DATA_ROOT", workflow)

    def test_fixed_source_and_two_distinct_frames_pass(self):
        result = audit_frames(self.source, self.sd, self.evidence, True)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertTrue(result["native_stage336_upload_receipt_verified"])
        self.assertTrue(result["native_texture_sampled_in_neixium_frame"])
        self.assertEqual(result["independent_frames_verified"], 2)
        self.assertEqual(result["samples_per_frame"], 25)
        self.assertEqual(result["frame_a"]["bad_channels"], 0)
        self.assertEqual(result["frame_b"]["bad_channels"], 0)
        self.assertNotIn("samples_private", result["frame_a"])
        self.assertNotIn("samples_private", result["frame_b"])
        self.assertNotIn("expected_rgb", json.dumps(result))
        self.assertNotIn("observed_rgb", json.dumps(result))
        self.assertFalse(result["physical_switch_verified"])

    def test_private_mode_uses_separate_runtime_checksum_and_no_public_metadata(self):
        (self.evidence / "generated-source.json").unlink()
        (self.evidence / "nexium-archive.sha256").rename(
            self.evidence / "nexium-runtime.sha256"
        )
        (self.evidence / "nexium-runtime.sha256").write_text(
            "b" * 64 + "  run-nexium.sh\n", encoding="ascii"
        )
        result = audit_frames(self.source, self.sd, self.evidence, False)
        self.assertEqual(result["generated_only"], False)
        self.assertEqual(result["independent_frames_verified"], 2)
        for frame in ("frame_a", "frame_b"):
            samples = result[frame]["samples_private"]
            self.assertEqual(len(samples), 25)
            self.assertEqual(samples[0]["frame_xy"], [SAMPLE_X[0], SAMPLE_Y[0]])
            self.assertEqual(len(samples[0]["expected_rgb"]), 3)
            self.assertEqual(len(samples[0]["observed_rgb"]), 3)
            self.assertEqual(samples[0]["absolute_rgb_error"], [0, 0, 0])
        with self.assertRaises(ValueError):
            audit_frames(self.source, self.sd, self.evidence, True)

    def test_invalid_or_compressed_dds_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_bgra8_dds(b"not-a-dds")
        data = bytearray(self.source.read_bytes())
        data[84:88] = b"DXT1"
        with self.assertRaises(ValueError):
            decode_bgra8_dds(bytes(data))

    def test_missing_or_forged_guest_receipt_is_rejected(self):
        (self.gpu / MARKER_NAME).write_bytes(b"FOJ_STAGE341 diff=0\n")
        with self.assertRaises(ValueError):
            audit_frames(self.source, self.sd, self.evidence, True)

    def test_duplicate_frames_are_rejected(self):
        (self.evidence / "gpu-later.png").write_bytes(
            (self.evidence / "gpu-initial.png").read_bytes()
        )
        with self.assertRaises(ValueError):
            audit_frames(self.source, self.sd, self.evidence, True)

    def test_wrong_pixels_fail_closed(self):
        bad = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), (255, 0, 255))
        bad.save(self.evidence / "gpu-later.png")
        with self.assertRaises(ValueError):
            audit_frames(self.source, self.sd, self.evidence, True)

    def test_stale_capture_predating_receipt_is_rejected(self):
        frame = self.evidence / "gpu-initial.png"
        old = self.gpu / MARKER_NAME
        import os
        os.utime(frame, ns=(old.stat().st_mtime_ns - 2_000_000_000,) * 2)
        with self.assertRaises(ValueError):
            audit_frames(self.source, self.sd, self.evidence, True)

    def test_extra_evidence_or_sd_input_is_rejected(self):
        (self.evidence / "unexpected.bin").write_bytes(b"x")
        with self.assertRaises(ValueError):
            audit_frames(self.source, self.sd, self.evidence, True)
        (self.evidence / "unexpected.bin").unlink()
        (self.gpu / "extra.dds").write_bytes(b"x")
        with self.assertRaises(ValueError):
            audit_frames(self.source, self.sd, self.evidence, True)


    def test_generated_failure_diagnostic_is_non_pixel_and_never_accepts(self):
        result = diagnose(self.sd, self.evidence)
        self.assertTrue(result["generated_only"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["frame_a"]["identity_bad_channels"], 0)
        self.assertEqual(result["frame_a"]["distinct_rgb_triplets_at_grid"], 25)
        centerlines = result["frame_a"]["generated_quad_centerline_bounds"]
        self.assertEqual(centerlines["horizontal_xy_pixels"], [128, 1151])
        self.assertEqual(centerlines["vertical_xy_pixels"], [72, 647])
        self.assertTrue(centerlines["independent_of_sample_grid"])
        self.assertEqual(result["frame_a"]["exact_generated_fixture_rgb_matches"], 25)
        self.assertEqual(result["frame_a"]["exact_expected_generated_texel_matches"], 25)
        self.assertEqual(result["frame_a"]["most_common_inverse_texel_offset"], [0, 0])
        self.assertEqual(
            result["frame_a"]["generated_texel_affine_mapping"]["rmse_texels"], 0.0
        )
        self.assertEqual(result["frame_b"]["identity_bad_channels"], 0)
        encoded = json.dumps(result)
        self.assertNotIn("expected_rgb", encoded)
        self.assertNotIn("observed_rgb", encoded)
        self.assertNotIn("samples_private", encoded)

    def test_generated_failure_diagnostic_catches_swapped_red_blue(self):
        for name in ("gpu-initial.png", "gpu-later.png"):
            path = self.evidence / name
            with Image.open(path) as original:
                source = original.convert("RGB")
            r, g, b = source.split()
            Image.merge("RGB", (b, g, r)).save(path)
        result = diagnose(self.sd, self.evidence)
        self.assertGreater(result["frame_a"]["identity_bad_channels"], 0)
        self.assertEqual(result["frame_a"]["bad_channels_by_hypothesis"]["swap_rb"], 0)
        self.assertFalse(result["accepted"])

    def test_generated_failure_diagnostic_detects_uniform_quad_region(self):
        Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), (20, 30, 40)).save(
            self.evidence / "gpu-initial.png"
        )
        Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), (40, 30, 20)).save(
            self.evidence / "gpu-later.png"
        )
        result = diagnose(self.sd, self.evidence)
        self.assertTrue(result["frame_a"]["uniform_grid_sample"])
        self.assertIsNone(
            result["frame_a"]["generated_quad_centerline_bounds"]["horizontal_xy_pixels"]
        )
        self.assertIsNone(
            result["frame_b"]["generated_quad_centerline_bounds"]["vertical_xy_pixels"]
        )
        self.assertTrue(result["frame_b"]["uniform_grid_sample"])
        self.assertEqual(result["frame_a"]["distinct_rgb_triplets_at_grid"], 1)
        self.assertEqual(result["frame_b"]["largest_repeated_rgb_triplet_count"], 25)
        self.assertFalse(result["accepted"])


    def test_generated_failure_diagnostic_identifies_integer_texel_shift(self):
        rgba = decode_bgra8_dds(self.source.read_bytes())
        for name in ("gpu-initial.png", "gpu-later.png"):
            path = self.evidence / name
            with Image.open(path) as original:
                image = original.convert("RGB")
            for y in SAMPLE_Y:
                for x in SAMPLE_X:
                    u, v = _sample_uv(x, y)
                    tx = min(255, max(0, int(u * 256) + 3))
                    ty = min(255, max(0, int(v * 256) - 2))
                    offset = (ty * 256 + tx) * 4
                    image.putpixel((x, y), tuple(rgba[offset:offset + 3]))
            image.save(path)
        result = diagnose(self.sd, self.evidence)
        self.assertFalse(result["accepted"])
        for frame in ("frame_a", "frame_b"):
            self.assertEqual(result[frame]["best_integer_texel_offset"], [3, -2])
            self.assertEqual(result[frame]["best_integer_texel_offset_bad_channels"], 0)
            self.assertEqual(result[frame]["exact_generated_fixture_rgb_matches"], 25)
            self.assertEqual(result[frame]["most_common_inverse_texel_offset"], [3, -2])
            self.assertEqual(result[frame]["largest_consistent_inverse_offset_votes"], 25)
            fit = result[frame]["generated_texel_affine_mapping"]
            self.assertEqual(fit["fit_points"], 25)
            self.assertLess(fit["max_abs_residual_texels"], 0.001)
            self.assertEqual(fit["source_texel_x_from_expected_xy"], [1.0, 0.0, 3.0])
            self.assertEqual(fit["source_texel_y_from_expected_xy"], [0.0, 1.0, -2.0])
            self.assertGreater(result[frame]["identity_bad_channels"], 0)


    def test_generated_failure_diagnostic_detects_alpha_premultiplication(self):
        rgba = decode_bgra8_dds(self.source.read_bytes())
        for name in ("gpu-initial.png", "gpu-later.png"):
            path = self.evidence / name
            with Image.open(path) as original:
                image = original.convert("RGB")
            for y in SAMPLE_Y:
                for x in SAMPLE_X:
                    u, v = _sample_uv(x, y)
                    tx = min(255, max(0, int(u * 256)))
                    ty = min(255, max(0, int(v * 256)))
                    offset = (ty * 256 + tx) * 4
                    alpha = rgba[offset + 3]
                    image.putpixel((x, y), tuple(
                        (rgba[offset + k] * alpha + 127) // 255
                        for k in range(3)
                    ))
            image.save(path)
        result = diagnose(self.sd, self.evidence)
        self.assertFalse(result["accepted"])
        for frame in ("frame_a", "frame_b"):
            self.assertEqual(
                result[frame]["alpha_composite_hypothesis_bad_channels"][
                    "premultiplied_black"
                ], 0
            )
            self.assertGreater(result[frame]["identity_bad_channels"], 0)

    def test_generated_fixture_rgb_inversion_unique_over_all_texels(self):
        for y in range(256):
            for x in range(256):
                rgb = ((3*x+5*y+17)&255, (11*x+7*y+23)&255,
                       (13*x+2*y+91)&255)
                self.assertEqual(invert_generated_rgb(rgb), (x,y))

    def test_generated_rgb_inversion_rejects_green_channel_tampering(self):
        for x, y in ((5, 6), (127, 127), (250, 248)):
            rgb = ((3*x+5*y+17)&255, (11*x+7*y+23)&255,
                   (13*x+2*y+91)&255)
            altered = (rgb[0], (rgb[1] + 1) & 255, rgb[2])
            self.assertIsNone(invert_generated_rgb(altered))

    def test_generated_failure_diagnostic_rejects_private_source(self):
        source = bytearray(self.source.read_bytes())
        source[-1] ^= 1
        self.source.write_bytes(source)
        with self.assertRaises(ValueError):
            diagnose(self.sd, self.evidence)

    def test_no_raw_pixels_or_sample_values_in_public_result(self):
        result = audit_frames(self.source, self.sd, self.evidence, True)
        encoded = json.dumps({
            "schema": result["schema"],
            "frame_a": {k: v for k, v in result["frame_a"].items() if k != "samples_private"},
            "frame_b": {k: v for k, v in result["frame_b"].items() if k != "samples_private"},
        })
        self.assertNotIn("expected_rgb", encoded)
        self.assertNotIn("observed_rgb", encoded)


if __name__ == "__main__":
    unittest.main()
