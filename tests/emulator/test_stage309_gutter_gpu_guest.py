"""Stage309 host-generated seam PNGs exercise refusal logic ONLY, not NeXium."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage309_gutter_gpu_guest import (
    MARKER,MARKER_BYTES,RECEIPT,_frame,audit,publish
)
def mock_gpu(root:Path):
    b=root/"bridge"
    b.mkdir(parents=True)
    for filename,data in (("generated-input.json",_origin()),
                          ("dds-before.json",_attestation("before")),
                          ("dds-after.json",_attestation("after"))):
        (b/filename).write_text(json.dumps(data))
    (b/MARKER).write_bytes(MARKER_BYTES)
    (b/"guest.log").write_text("only mock, not real GPU evidence")
    (root/"nexium-archive.sha256").write_text("a"*64+"  /tmp/nexium.tar.gz\n")
    for filename,bg in (("gpu-initial.png",(15,50,68)),
                        ("gpu-later.png",(65,32,51))):
        image=Image.new("RGB",(1280,720),bg)
        dr=ImageDraw.Draw(image)
        for row,lo,hi in ((280,(0,0,255),(255,255,0)),
                          (460,(255,0,0),(0,255,0))):
            dr.rectangle((270,row-40,639,row+40),fill=lo)
            dr.rectangle((640,row-40,1010,row+40),fill=hi)
            for x in range(621,659):
                t=(x-621)/37
                rgb=tuple(round(lo[i]*(1-t)+hi[i]*t) for i in range(3))
                dr.line(((x,row-40),(x,row+40)),fill=rgb)
        image.save(b/filename)
    (b/RECEIPT).write_text(json.dumps(audit(b)))

class Stage309HostMockTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.source=self.root/"generated-source"
        self.public=self.root/"public"
        mock_gpu(self.source)
        self.bridge=self.source/"bridge"

    def mutate(self,file,xy,fill):
        path=self.bridge/file
        with Image.open(path) as f:img=f.convert("RGB")
        ImageDraw.Draw(img).rectangle(xy,fill=fill)
        img.save(path)

    def test_two_contrasting_edge_pairs_and_true_mixed_center(self):
        result=audit(self.bridge)
        self.assertTrue(result["gpu_mixed_cross_page_color_verified"])
        self.assertEqual(result["real_neixum_frames_verified"],2)
        self.assertEqual(len(result["per_frame_probes"]["gpu-initial.png"]),6)
        self.assertFalse(result["hardware_filtering_on_independent_pages"])
        self.assertFalse(result["physical_switch_tested"])

    def test_left_color_wrong_refused(self):
        self.mutate("gpu-initial.png",(564,270,576,290),(0,0,0))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_right_color_wrong_refused(self):
        self.mutate("gpu-later.png",(702,450,717,470),(0,0,0))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_no_mixed_middle_refused(self):
        self.mutate("gpu-initial.png",(635,272,646,288),(0,0,255))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_clamp_to_single_page_never_accepted_as_blend(self):
        self.mutate("gpu-later.png",(635,448,646,472),(255,0,0))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_second_phase_must_exist(self):
        p=self.bridge/"gpu-later.png"
        p.write_bytes((self.bridge/"gpu-initial.png").read_bytes())
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_native_marker_required(self):
        (self.bridge/MARKER).write_text("untrusted\n")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_generated_origin_required(self):
        (self.bridge/"generated-input.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_dds_after_attestation_required(self):
        (self.bridge/"dds-after.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_publication_only_8_files(self):
        result=publish(self.source,self.public)
        self.assertEqual(result["public_files"],8)
        self.assertFalse((self.public/"bridge"/"guest.log").exists())
        self.assertEqual(audit(self.public/"bridge"),audit(self.bridge))

    def test_unknown_game_dds_refused(self):
        (self.bridge/"game-source.dds").write_bytes(b"owner-only")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_symlink_screen_refused(self):
        p=self.bridge/"gpu-later.png"
        p.unlink()
        p.symlink_to(self.bridge/"gpu-initial.png")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_forged_stale_receipt_refused(self):
        p=self.bridge/RECEIPT
        fake=json.loads(p.read_text())
        fake["gpu_mixed_cross_page_color_verified"]=False
        p.write_text(json.dumps(fake))
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_missing_neixum_archive_digest_refused(self):
        (self.source/"nexium-archive.sha256").unlink()
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertFalse(self.public.exists())

    def test_preexisting_destination_preserved(self):
        self.public.mkdir()
        (self.public/"keep").write_text("saved")
        with self.assertRaises(ValueError):publish(self.source,self.public)
        self.assertEqual((self.public/"keep").read_text(),"saved")

if __name__=="__main__":
    unittest.main()
