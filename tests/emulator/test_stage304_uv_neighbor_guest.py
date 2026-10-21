"""Stage304 mocked screenshot refusals only: NOT real NeXium evidence."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw

from tools.foj_stage273_dynamic_gpu_sd import expected_rgb
from tools.foj_stage274_pass_contract_check import expected_receipt
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage304_uv_neighbor_guest import (
    MARKER,MARKERS,RECEIPT,COLORS,audit,pixel_probe,pair,publish
)


def mock_case(parent:Path,side:str):
    bridge=parent/"bridge"
    bridge.mkdir(parents=True)
    for name,payload in (
        ("generated-input.json",_origin()),
        ("dds-before.json",_attestation("before")),
        ("dds-after.json",_attestation("after"))):
        (bridge/name).write_text(json.dumps(payload))
    (bridge/"native-sort-pass.txt").write_bytes(b"FOJ_NATIVE_SORT_V1 2,1,0\n")
    (bridge/"native-alpha-pass.txt").write_bytes(expected_receipt("original"))
    (bridge/MARKER).write_bytes(MARKERS[side])
    for name,background in (
        ("gpu-initial.png",(15,50,68)),
        ("gpu-later.png",(65,32,51))):
        img=Image.new("RGB",(1280,720),background)
        pen=ImageDraw.Draw(img)
        for x,y in ((640,400),(600,400)):
            pen.rectangle((x-5,y-5,x+5,y+5),fill=expected_rgb("original"))
        pen.rectangle((755,395,765,405),fill=COLORS[side])
        img.save(bridge/name)
    (bridge/"guest.log").write_text("mock generated-only test")
    (parent/"nexium-archive.sha256").write_text("a"*64+"  /tmp/nexium.tar.gz\n")
    (bridge/RECEIPT).write_text(json.dumps(audit(bridge,side)))


class Stage304MockAuditTests(unittest.TestCase):
    def setUp(self):
        root=tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root=Path(root.name)
        self.left=self.root/"source-left"
        self.right=self.root/"source-right"
        mock_case(self.left,"left")
        mock_case(self.right,"right")
        self.public_left=self.root/"public-left"
        self.public_right=self.root/"public-right"

    def test_both_generated_mock_sides_have_distinct_expected_colors(self):
        l=audit(self.left/"bridge","left")
        r=audit(self.right/"bridge","right")
        self.assertEqual(l["gpu_probe_matches"]["gpu-initial.png"],121)
        self.assertEqual(r["gpu_probe_matches"]["gpu-later.png"],121)
        self.assertNotEqual(l["expected_nearest_page_rgb"],r["expected_nearest_page_rgb"])
        self.assertFalse(l["original_game_uv_materials_verified"])
        self.assertFalse(r["single_triangle_across_seam_gpu_tested"])

    def test_wrong_side_probe_refused(self):
        with self.assertRaises(ValueError):
            pixel_probe(self.left/"bridge"/"gpu-initial.png","right")
        with self.assertRaises(ValueError):
            pixel_probe(self.right/"bridge"/"gpu-later.png","left")

    def test_wrong_native_guest_side_marker_refused(self):
        (self.left/"bridge"/MARKER).write_bytes(MARKERS["right"])
        with self.assertRaises(ValueError):
            audit(self.left/"bridge","left")

    def test_single_side_evidence_publication_strips_raw_log(self):
        publish(self.left,self.public_left,"left")
        self.assertFalse((self.public_left/"bridge"/"guest.log").exists())
        self.assertEqual(audit(self.public_left/"bridge","left"),
                         audit(self.left/"bridge","left"))

    def test_pair_accepts_only_two_differently_colored_mock_frames(self):
        publish(self.left,self.public_left,"left")
        publish(self.right,self.public_right,"right")
        result=pair(self.public_left,self.public_right)
        self.assertEqual(result["case_count"],2)
        self.assertEqual(result["total_real_guest_frames"],4)
        self.assertFalse(result["original_ps3_assets"])

    def test_pair_refuses_duplicate_right_frames(self):
        publish(self.left,self.public_left,"left")
        publish(self.right,self.public_right,"right")
        for name in ("gpu-initial.png","gpu-later.png"):
            body=(self.public_left/"bridge"/name).read_bytes()
            (self.public_right/"bridge"/name).write_bytes(body)
        with self.assertRaises(ValueError):
            pair(self.public_left,self.public_right)

    def test_private_file_never_published(self):
        (self.left/"bridge"/"original-foj-source.dds").write_bytes(b"private")
        with self.assertRaises(ValueError):
            publish(self.left,self.public_left,"left")
        self.assertFalse(self.public_left.exists())

    def test_wrong_pixel_color_fails_even_with_native_marker(self):
        path=self.right/"bridge"/"gpu-later.png"
        with Image.open(path) as img:
            modified=img.convert("RGB")
        ImageDraw.Draw(modified).rectangle((755,395,765,405),fill=COLORS["left"])
        modified.save(path)
        with self.assertRaises(ValueError):
            audit(self.right/"bridge","right")

    def test_invalid_report_prevents_public_copy(self):
        report=self.left/"bridge"/RECEIPT
        payload=json.loads(report.read_text())
        payload["selected_page"]={"x":0,"y":0}
        report.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            publish(self.left,self.public_left,"left")
        self.assertFalse(self.public_left.exists())

    def test_symlinked_guest_frame_rejected(self):
        bad=self.right/"bridge"/"gpu-later.png"
        bad.unlink()
        bad.symlink_to(self.right/"bridge"/"gpu-initial.png")
        with self.assertRaises(ValueError):
            publish(self.right,self.public_right,"right")
        self.assertFalse(self.public_right.exists())

    def test_wrong_opposite_marker_for_unique_near_seam(self):
        report=audit(self.left/"bridge","left")
        self.assertEqual(report["selected_uv_texel"],{"x":511,"y":384})
        self.assertEqual(audit(self.right/"bridge","right")["selected_uv_texel"],
                         {"x":512,"y":384})


if __name__=="__main__":
    unittest.main()
