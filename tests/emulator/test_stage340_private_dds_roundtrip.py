from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest

from tools.foj_stage340_fixture import create, fixture_bytes, verify
from tools.foj_stage340_receipt import MARKER, EXPECTED_PROGRESS, audit, publish
from tools.foj_stage340_private_run import private_source, write_report, REPO_ROOT


class Stage340PrivateDdsRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sd = self.root / "sdmc"
        self.gpu = self.sd / "switch" / "foj" / "gpu"
        self.gpu.mkdir(parents=True)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.source = self.gpu / "source.dds"
        self.marker = self.gpu / "foj-stage340-native-dds-roundtrip.txt"
        self.progress = self.gpu / "foj-stage340-progress.txt"
        create(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def write_guest_witnesses(self):
        self.marker.write_bytes(MARKER)
        self.progress.write_text(
            "".join(f"FOJ340P1 stage={n:02d}\n" for n in EXPECTED_PROGRESS),
            encoding="ascii",
        )

    def test_generated_fixture_is_exact_bounded_classic_bgra8(self):
        info = verify(self.source)
        self.assertEqual(self.source.stat().st_size, 262272)
        self.assertEqual(info["width"], 256)
        self.assertEqual(info["height"], 256)
        self.assertEqual(info["format"], "BGRA8")
        self.assertTrue(info["generated_only"])
        self.assertFalse(info["original_ps3_assets_used"])
        self.assertEqual(self.source.read_bytes(), fixture_bytes())

    def test_changed_fixture_is_rejected(self):
        data = bytearray(self.source.read_bytes())
        data[-1] ^= 0x80
        self.source.write_bytes(data)
        with self.assertRaises(ValueError):
            verify(self.source)

    def test_symlink_source_is_rejected(self):
        moved = self.gpu / "saved.dds"
        self.source.rename(moved)
        self.source.symlink_to(moved.name)
        with self.assertRaises(ValueError):
            verify(self.source)

    def test_actual_native_marker_and_full_progress_required(self):
        self.write_guest_witnesses()
        result = audit(self.sd, self.evidence)
        self.assertTrue(result["native_deko3d_upload_and_queue_wait"])
        self.assertTrue(result["native_deko3d_image_to_buffer_readback_and_fence"])
        self.assertEqual(result["different_channels"], 0)
        self.assertFalse(result["framebuffer_verified"])
        self.assertFalse(result["physical_switch_verified"])

    def test_forged_or_stale_success_marker_is_rejected(self):
        self.write_guest_witnesses()
        self.marker.write_bytes(b"STAGE340_DEKO3D_DDS_GPU_ROUNDTRIP_V1 diff=0\n")
        with self.assertRaises(ValueError):
            audit(self.sd, self.evidence)

    def test_incomplete_repeated_or_reordered_progress_is_rejected(self):
        self.marker.write_bytes(MARKER)
        self.progress.write_text(
            "FOJ340P1 stage=00\nFOJ340P1 stage=00\nFOJ340P1 stage=13\n",
            encoding="ascii",
        )
        with self.assertRaises(ValueError):
            audit(self.sd, self.evidence)

    def test_owner_private_source_preflight_accepts_generated_contract(self):
        blob, info, digest = private_source(self.source)
        self.assertEqual(blob, self.source.read_bytes())
        self.assertEqual(info["width"], 256)
        self.assertEqual(info["format"], "BGRA8")
        self.assertEqual(len(digest), 64)
        self.assertEqual(len(info["decoded_rgba_sha256_reference"]), 64)

    def test_owner_private_preflight_rejects_checkout_input_and_report(self):
        with self.assertRaises(ValueError):
            private_source(Path(__file__).resolve())
        with self.assertRaises(ValueError):
            write_report(REPO_ROOT / "stage340-private-test.json", {})

    def test_public_report_is_aggregate_only_and_refuses_overwrite(self):
        self.write_guest_witnesses()
        out = self.root / "aggregate.json"
        result = publish(self.sd, self.evidence, out)
        self.assertEqual(json.loads(out.read_text()), result)
        self.assertTrue(result["generated_only"])
        self.assertNotIn("source_path", result)
        self.assertNotIn("pixels", result)
        self.assertNotIn("guest_log", result)
        with self.assertRaises(ValueError):
            publish(self.sd, self.evidence, out)


if __name__ == "__main__":
    unittest.main()
