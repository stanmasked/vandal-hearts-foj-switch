"""Stage288 host-only negative regressions; mock frames never prove NeXium GPU."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw
from tools.foj_stage273_dynamic_gpu_sd import expected_rgb
from tools.foj_stage266_transparency_order import COOL
from tools.foj_stage274_pass_contract_check import expected_receipt
from tools.foj_stage288_generated_bridge_gpu import (
    SCHEMA, audit, attest, expected_hashes, ROOT_NAME,
)

SCENARIO = "original"


def create_mock_evidence(dest: Path) -> None:
    dest.mkdir()
    (dest / "generated-input.json").write_text(json.dumps({
        "schema": SCHEMA,
        "scenario": SCENARIO,
        "source": "generated-only Stage286 local DDS bridge",
        "generated_only": True,
        "original_ps3_resources": False,
        "actual_gpu_verified": False,
        "private_binding_manifest_archived": False,
        "expected_native_sort": [2, 1, 0],
        "expected_dds_sha256": expected_hashes(),
    }))
    for phase in ("before", "after"):
        (dest / f"dds-{phase}.json").write_text(json.dumps({
            "schema": SCHEMA, "phase": phase, "generated_only": True,
            "original_ps3_resources": False,
            "private_binding_manifest_archived": False,
            "material_slots_verified": 3,
            "dds_sha256": expected_hashes(),
        }))
    (dest / "native-sort-pass.txt").write_bytes(b"FOJ_NATIVE_SORT_V1 2,1,0\n")
    (dest / "native-alpha-pass.txt").write_bytes(expected_receipt("original"))
    for name, clear in (
        ("gpu-initial.png", (15, 50, 68)),
        ("gpu-later.png", (65, 32, 51)),
    ):
        image = Image.new("RGB", (1280, 720), clear)
        draw = ImageDraw.Draw(image)
        for p in ((640, 400), (600, 400)):
            draw.rectangle((p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5),
                           fill=expected_rgb("original"))
        p=(760,400)
        draw.rectangle((p[0]-5,p[1]-5,p[0]+5,p[1]+5),fill=COOL)
        image.save(dest / name)


class GeneratedThreeDDSGPUBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir=Path(self.temp.name) / "evidence"
        create_mock_evidence(self.dir)

    def test_mock_classifier_accepts_precisely_generated_receipts(self):
        result=audit(self.dir)
        self.assertEqual(result["verified_guest_frames"],2)
        self.assertEqual(result["material_slots"],3)
        self.assertTrue(result["canonical_dds_before_after_checked"])
        self.assertFalse(result["original_ps3_resources"])
        self.assertFalse(result["physical_switch_verified"])

    def test_wrong_sort_order_rejected(self):
        (self.dir / "native-sort-pass.txt").write_text("FOJ_NATIVE_SORT_V1 0,1,2\n")
        with self.assertRaisesRegex(ValueError, "native guest receipt"):
            audit(self.dir)

    def test_wrong_native_alpha_pass_rejected(self):
        (self.dir / "native-alpha-pass.txt").write_bytes(b"falsified\n")
        with self.assertRaisesRegex(ValueError, "native guest receipt"):
            audit(self.dir)

    def test_changed_dds_sha_rejected(self):
        path=self.dir / "dds-after.json"
        meta=json.loads(path.read_text())
        meta["dds_sha256"]["material2.dds"]="0"*64
        path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, "DDS observation mismatch"):
            audit(self.dir)

    def test_unsupported_provenance_rejected(self):
        path=self.dir / "generated-input.json"
        meta=json.loads(path.read_text())
        meta["original_ps3_resources"]=True
        path.write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, "provenance mismatch"):
            audit(self.dir)

    def test_private_manifest_leak_rejected(self):
        (self.dir / "owner-private-stage286-binding.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "private manifest leak"):
            audit(self.dir)

    def test_missing_guest_receipt_rejected(self):
        (self.dir / "native-sort-pass.txt").unlink()
        with self.assertRaisesRegex(ValueError, "native guest receipt"):
            audit(self.dir)

    def test_duplicate_frame_rejected(self):
        first=self.dir/"gpu-initial.png"
        (self.dir/"gpu-later.png").write_bytes(first.read_bytes())
        with self.assertRaisesRegex(ValueError, "duplicate guest frame"):
            audit(self.dir)

    def test_wrong_material_pixel_rejected(self):
        p=self.dir/"gpu-initial.png"
        with Image.open(p) as source:
            rgb=source.convert("RGB")
        ImageDraw.Draw(rgb).rectangle((634,394,646,406),fill=(0,0,0))
        rgb.save(p)
        with self.assertRaises(ValueError):
            audit(self.dir)

    def test_missing_second_observation_rejected(self):
        (self.dir/"dds-after.json").unlink()
        with self.assertRaises(OSError):
            audit(self.dir)

    def test_failed_attest_does_not_write_witness(self):
        with self.assertRaises((ValueError,OSError)):
            attest(Path(self.temp.name)/"missing",self.dir,"before")
        self.assertTrue((self.dir/"dds-before.json").exists())


if __name__=="__main__":
    unittest.main()
