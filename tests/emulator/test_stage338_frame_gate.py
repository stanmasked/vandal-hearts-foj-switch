"""Generated-only Stage338 frame evidence and native wiring regressions."""
from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tools.foj_stage330_corner_patch_guest import MARKER, RECEIPT
from test_stage330_corner_patch_guest import mock_evidence
from tools.foj_stage338_frame_gate import ALLOWLIST, publish

class FrameGateTests(unittest.TestCase):
    def setUp(self):
        t = TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.bridge, self.source = mock_evidence(self.root)

    def test_generated_source_frame_real_audit_and_private_capture_gate(self):
        result = publish(self.source, self.root / "public")
        self.assertEqual(result["real_neixium_frame_count"], 2)
        self.assertTrue(result["independent_stage330_pixel_oracle"])
        self.assertTrue(result["source_and_corner_tile_samplers_verified"])
        self.assertFalse(result["screenshots_published"])
        self.assertFalse(result["guest_log_published"])
        self.assertFalse(result["original_ps3_assets_used"])
        self.assertEqual(
            {p.name for p in (self.root / "public").iterdir()}, ALLOWLIST)
        self.assertEqual(
            json.loads((self.root / "public" / "stage338-frame-proof.json").read_text()),
            result)

    def test_duplicate_captured_frames_rejected(self):
        (self.bridge / "gpu-later.png").write_bytes(
            (self.bridge / "gpu-initial.png").read_bytes())
        with self.assertRaises(ValueError):
            publish(self.source, self.root / "public")

    def test_tampered_native_receipt_rejected(self):
        (self.bridge / RECEIPT).write_text("{}\n")
        with self.assertRaises(ValueError):
            publish(self.source, self.root / "public")

    def test_extra_file_and_stale_output_rejected(self):
        (self.source / "original-ps3.bin").write_bytes(b"refuse synthetic fixture")
        with self.assertRaises(ValueError):
            publish(self.source, self.root / "out")
        (self.source / "original-ps3.bin").unlink()
        (self.root / "out").mkdir()
        with self.assertRaises(ValueError):
            publish(self.source, self.root / "out")

    def test_native_stage336_actual_sampled_texture_path(self):
        source = Path("gpu/deko3d_clear_main.c").read_text()
        mk = Path("gpu/stage338_native_frame.mk").read_text()
        workflow = Path(".github/workflows/stage338-native-frame.yml").read_text()
        self.assertIn("FOJ_GPU_STAGE338_NATIVE_TEXTURE_DRAW", source)
        self.assertIn("foj_stage336_native_record_rgba_upload(", source)
        self.assertIn("texture_views[i]=stage338_source.image_view;", source)
        self.assertIn("atlas.width*4u,0u", source)
        self.assertIn("foj_stage336_native_release(&stage338_source)", source)
        self.assertIn("dkCmdBufBindTextures(cmd,DkStage_Fragment", source)
        self.assertIn("dkCmdBufDraw(cmd,DkPrimitive_Triangles", source)
        self.assertIn("gpu/stage336_native_upload.c", mk)
        self.assertIn("FOJ_GPU_STAGE338_NATIVE_TEXTURE_DRAW=1", mk)
        self.assertIn("foj_stage338_frame_gate publish", workflow)
        self.assertNotIn("runtime-evidence-public/bridge/gpu-initial.png", workflow)

if __name__ == "__main__":
    unittest.main()
