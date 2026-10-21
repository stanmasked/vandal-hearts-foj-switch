"""Stage305 host mock tests are safety regressions, NOT actual guest frames."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image,ImageDraw

from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage305_same_frame_bc1_guest import (
    COLORS,MARKER,MARKER_BYTES,RECEIPT,_frame,audit,publish
)


def fake_guest(root:Path)->None:
    bridge=root/"bridge"
    bridge.mkdir(parents=True)
    for name,report in (
        ("generated-input.json",_origin()),
        ("dds-before.json",_attestation("before")),
        ("dds-after.json",_attestation("after")),
    ):
        (bridge/name).write_text(json.dumps(report))
    (bridge/MARKER).write_bytes(MARKER_BYTES)
    (bridge/"guest.log").write_text("host-generated PNG; NOT actual guest")
    (root/"nexium-archive.sha256").write_text("a"*64+"  /tmp/nexium.tar.gz\n")
    for name,clear in (
        ("gpu-initial.png",(15,50,68)),
        ("gpu-later.png",(65,32,51)),
    ):
        image=Image.new("RGB",(1280,720),clear)
        pen=ImageDraw.Draw(image)
        # Both halves of one continuous screen-space rectangle.
        pen.rectangle((256,180,639,539),fill=COLORS["left"])
        pen.rectangle((640,180,1023,539),fill=COLORS["right"])
        image.save(bridge/name)
    (bridge/RECEIPT).write_text(json.dumps(audit(bridge)))


class Stage305HostOnlyEvidenceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.source=self.root/"source"
        fake_guest(self.source)
        self.bridge=self.source/"bridge"
        self.public=self.root/"public"

    def test_two_colored_pages_are_in_each_same_mock_frame(self):
        report=audit(self.bridge)
        self.assertTrue(report["two_distinct_bc1_pages_visible_in_same_gpu_frame"])
        self.assertEqual(report["real_neixum_guest_frames_verified"],2)
        self.assertEqual(report["same_frame_pixel_probes"]["gpu-initial.png"],
                         {"left":81,"right":81})
        self.assertFalse(report["original_game_uvs_verified"])
        self.assertFalse(report["bilinear_filtering_seam_verified"])

    def test_wrong_left_page_fails_without_weakening_color_tolerance(self):
        path=self.bridge/"gpu-initial.png"
        with Image.open(path) as src:image=src.convert("RGB")
        ImageDraw.Draw(image).rectangle((620,396,639,404),
                                       fill=COLORS["right"])
        image.save(path)
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_wrong_right_page_fails(self):
        path=self.bridge/"gpu-later.png"
        with Image.open(path) as src:image=src.convert("RGB")
        ImageDraw.Draw(image).rectangle((641,396,660,404),
                                       fill=COLORS["left"])
        image.save(path)
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_one_missing_page_is_not_gpu_proof(self):
        path=self.bridge/"gpu-initial.png"
        with Image.open(path) as src:image=src.convert("RGB")
        ImageDraw.Draw(image).rectangle((640,180,1023,539),
                                       fill=(15,50,68))
        image.save(path)
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_guest_native_marker_identity_required(self):
        (self.bridge/MARKER).write_bytes(
            b"FOJ_NATIVE_STAGE305_SPLIT_V1 left=2,1 right=1,1 uv=511/512 verts=15\n")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_exact_synthetic_origin_required(self):
        (self.bridge/"generated-input.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_invalid_before_dds_attestation_required(self):
        (self.bridge/"dds-before.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_two_frames_must_differ_outside_surface(self):
        path=self.bridge/"gpu-later.png"
        (path).write_bytes((self.bridge/"gpu-initial.png").read_bytes())
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_public_artifacts_exclude_raw_guest_log(self):
        report=publish(self.source,self.public)
        self.assertEqual(report["public_files"],8)
        self.assertFalse((self.public/"bridge"/"guest.log").exists())
        self.assertEqual(audit(self.public/"bridge"),audit(self.bridge))

    def test_added_private_dds_refused_before_export(self):
        (self.bridge/"foj-original.dds").write_bytes(b"original-not-for-publication")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_guest_png_symlink_refused(self):
        path=self.bridge/"gpu-later.png"
        path.unlink()
        path.symlink_to(self.bridge/"gpu-initial.png")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_stale_guest_receipt_refused(self):
        record=self.bridge/RECEIPT
        values=json.loads(record.read_text())
        values["page_uv_seam_screen_x"]=300
        record.write_text(json.dumps(values))
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_existing_public_folder_never_overwritten(self):
        self.public.mkdir()
        (self.public/"important").write_text("keep")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertEqual((self.public/"important").read_text(),"keep")

    def test_incorrect_neixum_archive_digest_refused(self):
        (self.source/"nexium-archive.sha256").write_text("invalid\n")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_full_synthetic_frame_not_original_game_claim(self):
        r=audit(self.bridge)
        self.assertFalse(r["original_ps3_assets_used"])
        self.assertFalse(r["single_unsplit_polygon_texture_seam_verified"])
        self.assertFalse(r["physical_switch_verified"])


if __name__=="__main__":
    unittest.main()
