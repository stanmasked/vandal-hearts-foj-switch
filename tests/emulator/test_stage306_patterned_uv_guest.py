"""Stage306 host-created images are negative tests, never NeXium proof."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage306_patterned_uv_guest import (
    MARKER,MARKER_BYTES,RECEIPT,COLORS,_frame,audit,publish
)

def fixture(root:Path)->None:
    bridge=root/"bridge"
    bridge.mkdir(parents=True)
    for name,obj in (("generated-input.json",_origin()),
                     ("dds-before.json",_attestation("before")),
                     ("dds-after.json",_attestation("after"))):
        (bridge/name).write_text(json.dumps(obj))
    (bridge/MARKER).write_bytes(MARKER_BYTES)
    (bridge/"guest.log").write_text("host-generated mock; never guest evidence")
    (root/"nexium-archive.sha256").write_text("a"*64+"  /tmp/nexium.tar.gz\n")
    for name,bg in (("gpu-initial.png",(15,50,68)),
                    ("gpu-later.png",(65,32,51))):
        frame=Image.new("RGB",(1280,720),bg)
        painter=ImageDraw.Draw(frame)
        for side,start in (("left",256),("right",640)):
            for band,color in enumerate(COLORS[side]):
                painter.rectangle((start+96*band,180,
                                   start+96*(band+1)-1,539),fill=color)
        frame.save(bridge/name)
    (bridge/RECEIPT).write_text(json.dumps(audit(bridge)))

class Stage306SyntheticAuditTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"input"
        fixture(self.source)
        self.frames=self.source/"bridge"
        self.public=self.root/"output"

    def test_eight_distinct_interpolated_bands_in_one_frame(self):
        report=audit(self.frames)
        self.assertTrue(report["two_patterned_bc1_pages_visible_in_same_gpu_frame"])
        self.assertEqual(report["interpolated_uv_bands_verified"],8)
        self.assertTrue(report["matching_page_edge_color_verified"])
        self.assertEqual(report["real_neixum_guest_frames_verified"],2)
        self.assertEqual(len(report["same_frame_pixel_probes"]["gpu-initial.png"]),8)
        self.assertTrue(all(v==81 for v in
            report["same_frame_pixel_probes"]["gpu-initial.png"].values()))
        self.assertFalse(report["bilinear_filtering_seam_verified"])

    def modify(self,name,box,color):
        path=self.frames/name
        with Image.open(path) as original:
            img=original.convert("RGB")
        ImageDraw.Draw(img).rectangle(box,fill=color)
        img.save(path)

    def test_wrong_second_band_refused(self):
        self.modify("gpu-initial.png",(397,394,404,406),COLORS["left"][0])
        with self.assertRaises(ValueError):audit(self.frames)

    def test_static_page_color_refused_even_if_seam_ok(self):
        self.modify("gpu-later.png",(256,180,447,539),COLORS["left"][3])
        with self.assertRaises(ValueError):audit(self.frames)

    def test_reversed_band_order_refused(self):
        self.modify("gpu-initial.png",(970,394,981,407),COLORS["right"][0])
        with self.assertRaises(ValueError):audit(self.frames)

    def test_cross_page_black_crack_refused(self):
        self.modify("gpu-initial.png",(636,390,643,410),(0,0,0))
        with self.assertRaises(ValueError):audit(self.frames)

    def test_cross_page_red_leak_refused(self):
        self.modify("gpu-later.png",(646,400,648,401),(255,0,0))
        with self.assertRaises(ValueError):audit(self.frames)

    def test_native_guest_marker_is_required(self):
        (self.frames/MARKER).write_text("STAGE306_FAKE\n")
        with self.assertRaises(ValueError):audit(self.frames)

    def test_independent_dds_before_after_required(self):
        (self.frames/"dds-after.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.frames)

    def test_clear_phases_must_differ(self):
        target=self.frames/"gpu-later.png"
        target.write_bytes((self.frames/"gpu-initial.png").read_bytes())
        with self.assertRaises(ValueError):audit(self.frames)

    def test_exact_publication_strips_raw_log(self):
        p=publish(self.source,self.public)
        self.assertEqual(p["public_files"],8)
        self.assertFalse((self.public/"bridge"/"guest.log").exists())
        self.assertEqual(audit(self.public/"bridge"),audit(self.frames))

    def test_private_game_file_is_never_copied(self):
        (self.frames/"private-game.dds").write_bytes(b"not for publication")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_symlink_frame_refused(self):
        p=self.frames/"gpu-later.png"
        p.unlink()
        p.symlink_to(self.frames/"gpu-initial.png")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_stale_report_fails_closed(self):
        p=self.frames/RECEIPT
        d=json.loads(p.read_text())
        d["interpolated_uv_bands_verified"]=0
        p.write_text(json.dumps(d))
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_preexisting_export_not_overwritten(self):
        self.public.mkdir()
        (self.public/"keep").write_text("keep")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertEqual((self.public/"keep").read_text(),"keep")

    def test_original_assets_and_hardware_never_attested(self):
        r=audit(self.frames)
        self.assertFalse(r["original_ps3_assets_used"])
        self.assertFalse(r["original_game_uvs_verified"])
        self.assertFalse(r["physical_switch_verified"])
        self.assertFalse(r["single_unsplit_polygon_texture_seam_verified"])

if __name__=="__main__":
    unittest.main()
