"""Host-only mock images verify Stage310 evidence *refusal*, never NeXium."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage310_row_gutter_guest import (
    LEFT565,RIGHT565,Y_CENTERS,MARKER,MARKER_BYTES,RECEIPT,
    expand565,_frame,audit,publish,PUBLIC
)

EDGES=(173,216,260,303,347,390,433,477,520)
def mock(root:Path):
    b=root/"bridge";b.mkdir(parents=True)
    for n,data in (("generated-input.json",_origin()),
                   ("dds-before.json",_attestation("before")),
                   ("dds-after.json",_attestation("after"))):
        (b/n).write_text(json.dumps(data))
    (b/MARKER).write_bytes(MARKER_BYTES)
    (b/"guest.log").write_text("synthetic mock, not real guest GPU proof")
    (root/"nexium-archive.sha256").write_text("a"*64+"  /tmp/nexium.tar.gz\n")
    for file,bg in (("gpu-initial.png",(15,50,68)),
                    ("gpu-later.png",(65,32,51))):
        image=Image.new("RGB",(1280,720),bg)
        draw=ImageDraw.Draw(image)
        for band in range(8):
            lo=expand565(LEFT565[band]);ri=expand565(RIGHT565[band])
            y0,y1=EDGES[band],EDGES[band+1]-1
            draw.rectangle((270,y0,639,y1),fill=lo)
            draw.rectangle((640,y0,1010,y1),fill=ri)
            for x in range(621,659):
                f=(x-621)/37
                mixed=tuple(round(a*(1-f)+b*f) for a,b in zip(lo,ri))
                draw.line(((x,y0),(x,y1)),fill=mixed)
        image.save(b/file)
    (b/RECEIPT).write_text(json.dumps(audit(b)))

class Stage310NegativeHostMockTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.source=self.root/"source"
        self.dest=self.root/"public"
        mock(self.source)
        self.bridge=self.source/"bridge"

    def change(self,name,box,color):
        p=self.bridge/name
        with Image.open(p) as im:pic=im.convert("RGB")
        ImageDraw.Draw(pic).rectangle(box,fill=color)
        pic.save(p)

    def test_eight_bands_in_two_frames(self):
        x=audit(self.bridge)
        self.assertEqual(x["color_pairs_per_frame"],8)
        self.assertEqual(x["real_neixum_guest_frames_verified"],2)
        self.assertEqual(len(x["per_frame_pixel_probes"]["gpu-initial.png"]),24)
        self.assertTrue(x["all_eight_gpu_edge_color_pairs_and_midpoints_verified"])
        self.assertFalse(x["independent_sampler_cross_page_bilinear_verified"])

    def test_wrong_left_color_in_late_band(self):
        y=Y_CENTERS[6]
        self.change("gpu-initial.png",(564,y-4,576,y+4),(255,0,0))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_wrong_right_color_in_early_band(self):
        y=Y_CENTERS[1]
        self.change("gpu-later.png",(704,y-4,716,y+4),(0,0,0))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_wrong_gutter_midpoint(self):
        y=Y_CENTERS[3]
        self.change("gpu-initial.png",(636,y-4,644,y+4),(0,0,0))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_clamped_left_at_seam_rejected(self):
        y=Y_CENTERS[4]
        self.change("gpu-later.png",(635,y-4,645,y+4),expand565(LEFT565[4]))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_phase_must_change(self):
        (self.bridge/"gpu-later.png").write_bytes(
            (self.bridge/"gpu-initial.png").read_bytes())
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_forbidden_private_file_never_uploaded(self):
        (self.bridge/"user-data.dds").write_bytes(b"private")
        with self.assertRaises(ValueError):publish(self.source,self.dest)
        self.assertFalse(self.dest.exists())

    def test_symbolic_link_rejected(self):
        p=self.bridge/"gpu-later.png"
        p.unlink();p.symlink_to(self.bridge/"gpu-initial.png")
        with self.assertRaises(ValueError):publish(self.source,self.dest)
        self.assertFalse(self.dest.exists())

    def test_native_receipt_mismatch(self):
        (self.bridge/MARKER).write_bytes(b"wrong")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_source_attestation_mismatch(self):
        (self.bridge/"dds-after.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_forged_report_disallowed(self):
        p=self.bridge/RECEIPT
        x=json.loads(p.read_text())
        x["color_pairs_per_frame"]=0
        p.write_text(json.dumps(x))
        with self.assertRaises(ValueError):publish(self.source,self.dest)

    def test_generated_only_eight_file_publication(self):
        result=publish(self.source,self.dest)
        self.assertEqual(result["public_files"],8)
        self.assertEqual(len(PUBLIC),8)
        self.assertFalse((self.dest/"bridge"/"guest.log").exists())
        self.assertEqual(audit(self.bridge),audit(self.dest/"bridge"))

    def test_do_not_overwrite_prior_evidence(self):
        self.dest.mkdir()
        (self.dest/"keep").write_text("kept")
        with self.assertRaises(ValueError):publish(self.source,self.dest)
        self.assertEqual((self.dest/"keep").read_text(),"kept")

if __name__=="__main__":
    unittest.main()
