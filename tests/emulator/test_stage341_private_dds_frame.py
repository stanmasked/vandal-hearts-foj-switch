from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

from tools.foj_stage340_fixture import create, fixture_bytes
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

    def test_fixed_source_and_two_distinct_frames_pass(self):
        result = audit_frames(self.source, self.sd, self.evidence, True)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertTrue(result["native_stage336_upload_receipt_verified"])
        self.assertTrue(result["native_texture_sampled_in_neixium_frame"])
        self.assertEqual(result["independent_frames_verified"], 2)
        self.assertEqual(result["samples_per_frame"], 25)
        self.assertEqual(result["frame_a"]["bad_channels"], 0)
        self.assertEqual(result["frame_b"]["bad_channels"], 0)
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
