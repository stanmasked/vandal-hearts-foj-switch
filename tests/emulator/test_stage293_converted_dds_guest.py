"""Stage293 synthetic-only negative regressions: mock frames NEVER prove GPU."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET, WARM, COOL
from tools.foj_stage273_dynamic_gpu_sd import expected_rgb
from tools.foj_stage274_pass_contract_check import expected_receipt
from tools.foj_stage292_synthetic_gtf_dds_roundtrip import (
    convert_fixture, generate_solid_fixture,
)
from tools.foj_stage293_converted_dds_guest import (
    COLORS, RECEIPT, SCHEMA, _origin, _attestation,
    audit, converted, hashes, publish,
)


def synthetic_host_only_evidence(root: Path):
    root.mkdir(parents=True)
    for name, data in (
        ("generated-input.json", _origin()),
        ("dds-before.json", _attestation("before")),
        ("dds-after.json", _attestation("after")),
    ):
        (root / name).write_text(json.dumps(data))
    (root / "native-sort-pass.txt").write_bytes(b"FOJ_NATIVE_SORT_V1 2,1,0\n")
    (root / "native-alpha-pass.txt").write_bytes(expected_receipt("original"))
    for name, background in (
        ("gpu-initial.png", (15, 50, 68)),
        ("gpu-later.png", (65, 32, 51)),
    ):
        image = Image.new("RGB", (1280, 720), background)
        draw = ImageDraw.Draw(image)
        for point in ((640, 400), (600, 400)):
            x, y = point
            draw.rectangle((x-5, y-5, x+5, y+5), fill=expected_rgb("original"))
        x, y = (760, 400)
        draw.rectangle((x-5, y-5, x+5, y+5), fill=COOL)
        image.save(root / name)


class Stage293ConvertedDdsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bridge = self.root / "runtime-evidence" / "bridge"
        synthetic_host_only_evidence(self.bridge)
        self.evidence = self.bridge.parent
        (self.evidence / "nexium-archive.sha256").write_text(
            "a" * 64 + "  /tmp/nexium.tar.gz\n")
        (self.bridge / "guest.log").write_text("host-only placeholder\n")
        (self.bridge / RECEIPT).write_text(json.dumps(audit(self.bridge)))
        self.public = self.root / "public"

    def test_three_true_converted_outputs_instead_of_stage288_fallback(self):
        output = converted()
        self.assertEqual(set(output), {"material0.dds","material1.dds","material2.dds"})
        for name, color in zip(output, COLORS):
            with self.subTest(name=name):
                self.assertNotEqual(output[name], generated_dds(color))
                self.assertEqual(output[name][128:], bytes(color) * 4096)
                self.assertEqual(
                    output[name],
                    convert_fixture(generate_solid_fixture(color))[0],
                )

    def test_preexisting_stage292_gradient_remains_unchanged(self):
        original = bytes((17,61,103,128))
        data, note = convert_fixture(
            __import__("tools.foj_stage292_synthetic_gtf_dds_roundtrip", fromlist=["generate_fixture"]).generate_fixture(64,64,1,False))
        self.assertEqual(note["synthetic_fixture_mode"], "gradient")
        self.assertEqual(data[128:132], original)

    def test_no_owner_assets_claimed_in_any_source_report(self):
        self.assertFalse(audit(self.bridge)["original_ps3_resources"])
        self.assertTrue(_origin()["stage292_converter_executed"])
        self.assertEqual(_attestation("before")["dds_sha256"], hashes())
        self.assertFalse(audit(self.bridge)["physical_switch_verified"])

    def test_invalid_stage292_color_rejected_before_staging(self):
        for bad in ((1,2,3), (1,2,3,256), [1,2,3,4], (1,2,True,3)):
            with self.subTest(color=bad), self.assertRaises(ValueError):
                generate_solid_fixture(bad)

    def test_claimed_wrong_conversion_hash_fails(self):
        p = self.bridge / "dds-after.json"
        report = json.loads(p.read_text())
        report["dds_sha256"]["material2.dds"] = "0"*64
        p.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "identity"):
            audit(self.bridge)

    def test_old_stage288_hashes_cannot_replace_converted_provenance(self):
        p = self.bridge / "generated-input.json"
        report = json.loads(p.read_text())
        report["expected_converted_dds_sha256"]["material0.dds"] = "0"*64
        p.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "provenance"):
            audit(self.bridge)

    def test_wrong_native_material_receipt_fails(self):
        (self.bridge / "native-alpha-pass.txt").write_text("synthetic spoof")
        with self.assertRaisesRegex(ValueError, "guest receipt"):
            audit(self.bridge)

    def test_duplicate_frame_fails(self):
        (self.bridge / "gpu-later.png").write_bytes(
            (self.bridge / "gpu-initial.png").read_bytes())
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit(self.bridge)

    def test_corrupt_guest_material_pixels_fails(self):
        path = self.bridge / "gpu-initial.png"
        with Image.open(path) as image:
            rgb = image.convert("RGB")
        ImageDraw.Draw(rgb).rectangle((634, 394, 646, 406), fill=(0,0,0))
        rgb.save(path)
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_real_private_manifest_in_evidence_fails(self):
        (self.bridge / "owner-private-stage286-binding.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "private"):
            audit(self.bridge)

    def test_exact_public_export_has_nine_files_no_raw_logs(self):
        report = publish(self.evidence, self.public)
        self.assertEqual(report["public_files"], 9)
        self.assertFalse(report["raw_guest_log_uploaded"])
        self.assertFalse((self.public / "bridge" / "guest.log").exists())
        self.assertFalse((self.public / "bridge" / "owner-private-stage286-binding.json").exists())
        self.assertEqual(audit(self.public / "bridge"), audit(self.bridge))

    def test_unknown_dds_in_source_refused_without_output(self):
        (self.bridge / "unexpected.dds").write_bytes(b"untrusted")
        with self.assertRaisesRegex(ValueError, "unexpected"):
            publish(self.evidence, self.public)
        self.assertFalse(self.public.exists())

    def test_wrong_report_rejected_before_public_copy(self):
        p = self.bridge / RECEIPT
        report = json.loads(p.read_text())
        report["guest_frames_verified"] = 99
        p.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "re-audit"):
            publish(self.evidence, self.public)
        self.assertFalse(self.public.exists())

    def test_symlink_in_private_evidence_refused(self):
        p = self.bridge / "gpu-later.png"
        p.unlink()
        p.symlink_to("gpu-initial.png")
        with self.assertRaisesRegex(ValueError, "symlink"):
            publish(self.evidence, self.public)
        self.assertFalse(self.public.exists())

    def test_preexisting_public_path_never_overwritten(self):
        self.public.mkdir()
        marker = self.public / "keep"
        marker.write_text("important")
        with self.assertRaisesRegex(ValueError, "fresh"):
            publish(self.evidence, self.public)
        self.assertEqual(marker.read_text(), "important")

    def test_missing_neixum_provenance_refused(self):
        (self.evidence / "nexium-archive.sha256").unlink()
        with self.assertRaises(ValueError):
            publish(self.evidence, self.public)
        self.assertFalse(self.public.exists())

    def test_malformed_neixum_archive_sha_rejected(self):
        (self.evidence / "nexium-archive.sha256").write_text("bogus\n")
        with self.assertRaisesRegex(ValueError, "provenance"):
            publish(self.evidence, self.public)
        self.assertFalse(self.public.exists())


if __name__ == "__main__":
    unittest.main()
