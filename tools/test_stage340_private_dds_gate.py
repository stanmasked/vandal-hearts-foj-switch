import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools import foj_stage340_private_dds_gate as gate


class Stage340PrivateDdsGateTests(unittest.TestCase):
    def test_fixture_header_and_rgba_decode(self):
        data = gate.make_synthetic_dds()
        meta, rgba = gate._decode_rgba(data)
        self.assertEqual(meta["width"], 64)
        self.assertEqual(meta["height"], 64)
        self.assertEqual(meta["format"], "BGRA32")
        self.assertEqual(len(rgba), 64 * 64 * 4)
        self.assertEqual(gate._generated_input(data)["original_ps3_assets_used"], False)

    def test_frame_oracle_accepts_generated_nearest_texture(self):
        data = gate.make_synthetic_dds()
        _, rgba = gate._decode_rgba(data)
        with tempfile.TemporaryDirectory() as temp:
            frame_path = Path(temp) / "frame.png"
            with Image.frombytes("RGBA", (64, 64), rgba) as source:
                source.resize(gate.FRAME_SIZE, Image.Resampling.NEAREST).convert("RGB").save(frame_path)
            result = gate.audit_frame(frame_path, data)
            self.assertTrue(result["pass"])
            self.assertEqual(result["orientation"], "top-left")
            self.assertGreaterEqual(result["matched_samples"], 20)

    def test_frame_oracle_refuses_unrelated_solid_frame(self):
        data = gate.make_synthetic_dds()
        with tempfile.TemporaryDirectory() as temp:
            frame_path = Path(temp) / "wrong.png"
            Image.new("RGB", gate.FRAME_SIZE, (12, 12, 12)).save(frame_path)
            with self.assertRaises(ValueError):
                gate.audit_frame(frame_path, data)

    def test_marker_is_exact_and_stale_marker_is_not_accepted(self):
        self.assertEqual(gate.MARKER_BYTES,
                         b"FOJ_STAGE340_PRIVATE_DDS_GPU_V1 frame=1 upload=1 sample_draw=1\n")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            marker = root / gate.MARKER_NAME
            marker.write_bytes(gate.MARKER_BYTES + b"extra")
            with self.assertRaises(ValueError):
                gate._validate_marker(root)

    def test_private_source_cannot_be_published_as_generated(self):
        private_receipt = {
            "schema": gate.SCHEMA,
            "source_kind": "owner-original-ps3-dds",
            "generated_only": False,
            "original_ps3_assets_used": True,
            "user_dds_files_read": True,
        }
        self.assertNotEqual(private_receipt["source_kind"], "generated-only")
        self.assertFalse(private_receipt["generated_only"])


if __name__ == "__main__":
    unittest.main()
