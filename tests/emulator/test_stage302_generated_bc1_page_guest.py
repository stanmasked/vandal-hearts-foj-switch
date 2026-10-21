"""Stage302 host mocks test refusals only; GPU proof requires real CI NeXium."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from tools.foj_stage273_dynamic_gpu_sd import expected_rgb
from tools.foj_stage274_pass_contract_check import expected_receipt
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage302_generated_bc1_page_guest import (
    EXPECTED_MARKER,MARKER,RECEIPT,audit,pixel_probe,publish,
)


def make_mock(root):
    root.mkdir(parents=True)
    for name,body in (
        ("generated-input.json",_origin()),
        ("dds-before.json",_attestation("before")),
        ("dds-after.json",_attestation("after")),
    ):
        (root/name).write_text(json.dumps(body))
    (root/"native-sort-pass.txt").write_bytes(b"FOJ_NATIVE_SORT_V1 2,1,0\n")
    (root/"native-alpha-pass.txt").write_bytes(expected_receipt("original"))
    (root/MARKER).write_bytes(EXPECTED_MARKER)
    for name,background in (
        ("gpu-initial.png",(15,50,68)),
        ("gpu-later.png",(65,32,51)),
    ):
        img=Image.new("RGB",(1280,720),background)
        draw=ImageDraw.Draw(img)
        for x,y in ((640,400),(600,400)):
            draw.rectangle((x-5,y-5,x+5,y+5),
                           fill=expected_rgb("original"))
        x,y=(760,400)
        draw.rectangle((x-5,y-5,x+5,y+5),fill=(25,202,222))
        img.save(root/name)


class Stage302GuestAuditMockTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.source=self.root/"source"
        self.bridge=self.source/"bridge"
        make_mock(self.bridge)
        (self.bridge/"guest.log").write_text("host-only mock; not guest evidence\n")
        (self.source/"nexium-archive.sha256").write_text(
            "a"*64+"  /tmp/nexium.tar.gz\n")
        (self.bridge/RECEIPT).write_text(json.dumps(audit(self.bridge)))
        self.output=self.root/"public"

    def test_mock_contract_is_not_original_asset_or_hardware_proof(self):
        evidence=audit(self.bridge)
        self.assertEqual(evidence["real_neixum_guest_frames_verified"],2)
        self.assertTrue(evidence["generated_only"])
        self.assertFalse(evidence["original_1024_game_atlas_gpu_verified"])
        self.assertFalse(evidence["physical_switch_verified"])

    def test_rear_page_must_be_selected_quantized_color(self):
        for name in ("gpu-initial.png","gpu-later.png"):
            self.assertEqual(pixel_probe(self.bridge/name),121)

    def test_original_cool_fallback_is_rejected(self):
        image=self.bridge/"gpu-initial.png"
        with Image.open(image) as img:
            out=img.convert("RGB")
        ImageDraw.Draw(out).rectangle(
            (755,395,765,405),fill=(21,202,219))
        out.save(image)
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_guest_marker_missing_refused(self):
        (self.bridge/MARKER).unlink()
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_guest_marker_spoofed_coordinates_refused(self):
        (self.bridge/MARKER).write_text("FOJ_NATIVE_STAGE302_PAGE_V1 p=0,0 rgb=25,202,222 size=256\n")
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_corrupt_sort_receipt_refused(self):
        (self.bridge/"native-sort-pass.txt").write_text("untrusted\n")
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_public_export_exactly_10_files(self):
        result=publish(self.source,self.output)
        self.assertEqual(result["public_files"],10)
        self.assertFalse((self.output/"bridge"/"guest.log").exists())
        self.assertEqual(audit(self.output/"bridge"),audit(self.bridge))

    def test_private_file_refused_before_copy(self):
        (self.bridge/"original-source.dds").write_bytes(b"private game data")
        with self.assertRaises(ValueError):
            publish(self.source,self.output)
        self.assertFalse(self.output.exists())

    def test_symlink_frame_refused_before_copy(self):
        p=self.bridge/"gpu-later.png"
        p.unlink()
        p.symlink_to(self.bridge/"gpu-initial.png")
        with self.assertRaises(ValueError):
            publish(self.source,self.output)
        self.assertFalse(self.output.exists())

    def test_tampered_saved_report_refused(self):
        p=self.bridge/RECEIPT
        result=json.loads(p.read_text())
        result["selected_page"]["x"]=0
        p.write_text(json.dumps(result))
        with self.assertRaises(ValueError):
            publish(self.source,self.output)
        self.assertFalse(self.output.exists())

    def test_preexisting_public_destination_not_overwritten(self):
        self.output.mkdir()
        marker=self.output/"keep.txt"
        marker.write_text("important")
        with self.assertRaises(ValueError):
            publish(self.source,self.output)
        self.assertEqual(marker.read_text(),"important")

    def test_missing_neixum_provenance_refused(self):
        (self.source/"nexium-archive.sha256").unlink()
        with self.assertRaises(ValueError):
            publish(self.source,self.output)
        self.assertFalse(self.output.exists())

    def test_source_filename_and_game_artifacts_never_in_receipt(self):
        data=json.dumps(audit(self.bridge))
        self.assertNotIn("owner-private-stage286-binding",data)
        self.assertNotIn("original-source.dds",data)


if __name__=="__main__":
    unittest.main()
