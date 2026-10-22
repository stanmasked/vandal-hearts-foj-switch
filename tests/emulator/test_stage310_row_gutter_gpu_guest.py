"""Stage310 fabricated PNGs are host-only rejection tests, never guest proof."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage310_row_gutter_gpu_guest import (
    BANDS,MARKER,MARKER_BYTES,RECEIPT,_frame,audit,publish
)

def make_mock(root:Path):
    d=root/"bridge"
    d.mkdir(parents=True)
    for name,obj in (("generated-input.json",_origin()),
                     ("dds-before.json",_attestation("before")),
                     ("dds-after.json",_attestation("after"))):
        (d/name).write_text(json.dumps(obj))
    (d/MARKER).write_bytes(MARKER_BYTES)
    (d/"guest.log").write_text("Host fabricated frames, never real NeXium")
    (root/"nexium-archive.sha256").write_text("a"*64+"  /tmp/nexium.tar.gz\n")
    for name,bg in (("gpu-initial.png",(15,50,68)),
                    ("gpu-later.png",(65,32,51))):
        im=Image.new("RGB",(1280,720),bg)
        dr=ImageDraw.Draw(im)
        for stripe in range(8):
            top=188+stripe*43
            bottom=top+42
            left,right=BANDS[0][stripe],BANDS[1][stripe]
            dr.rectangle((270,top,639,bottom),fill=left)
            dr.rectangle((640,top,1010,bottom),fill=right)
            for x in range(621,660):
                t=(x-621)/38
                mix=tuple(round(left[k]*(1-t)+right[k]*t)
                          for k in range(3))
                dr.line(((x,top),(x,bottom)),fill=mix)
        im.save(d/name)
    (d/RECEIPT).write_text(json.dumps(audit(d)))

class GeneratedNegativeTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.src=self.root/"source"
        self.dst=self.root/"public"
        make_mock(self.src)
        self.bridge=self.src/"bridge"

    def draw_bad(self,file,box,color):
        p=self.bridge/file
        with Image.open(p) as source:
            im=source.convert("RGB")
        ImageDraw.Draw(im).rectangle(box,fill=color)
        im.save(p)

    def test_exact_eight_stripes_and_two_clears(self):
        r=audit(self.bridge)
        self.assertEqual(r["stripes_verified_per_frame"],8)
        self.assertEqual(r["two_actual_guest_frames_verified"],2)
        for bands in r["observed"].values():
            self.assertEqual(len(bands),8)
            ys=[bands[str(i)]["y"] for i in range(8)]
            self.assertEqual(ys,sorted(ys))
            self.assertTrue(all(bands[str(i)]["match"]["mixed"]>=22
                                for i in range(8)))
        self.assertFalse(r["hardware_cross_texture_bilinear_verified"])

    def test_missing_one_right_page_band(self):
        self.draw_bad("gpu-initial.png",(695,188+3*43,730,188+3*43+42),(1,2,3))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_gutter_single_page_clamp_rejected(self):
        self.draw_bad("gpu-later.png",(630,188+5*43,650,188+5*43+42),
                      BANDS[0][5])
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_missing_entire_stripe(self):
        self.draw_bad("gpu-initial.png",(268,188+7*43,1012,188+7*43+42),
                      (12,18,24))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_swapped_color_order(self):
        self.draw_bad("gpu-later.png",(268,188+1*43,1012,188+1*43+42),
                      (9,9,9))
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_forged_native_marker(self):
        (self.bridge/MARKER).write_text("Stage310: ok\n")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_same_background_clear_phase(self):
        (self.bridge/"gpu-later.png").write_bytes(
            (self.bridge/"gpu-initial.png").read_bytes())
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_modified_generated_dds_attestation(self):
        (self.bridge/"dds-after.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.bridge)

    def test_export_eight_files_and_no_raw_log(self):
        result=publish(self.src,self.dst)
        self.assertEqual(result["public_files"],8)
        self.assertFalse((self.dst/"bridge"/"guest.log").exists())
        self.assertEqual(audit(self.dst/"bridge"),audit(self.bridge))

    def test_extra_original_resource_refused(self):
        (self.bridge/"NPEB00148.dds").write_bytes(b"original")
        with self.assertRaises(ValueError):publish(self.src,self.dst)
        self.assertFalse(self.dst.exists())

    def test_png_symlink_refused(self):
        p=self.bridge/"gpu-later.png"
        p.unlink()
        p.symlink_to(self.bridge/"gpu-initial.png")
        with self.assertRaises(ValueError):publish(self.src,self.dst)

    def test_tampered_receipt_refused(self):
        p=self.bridge/RECEIPT
        o=json.loads(p.read_text())
        o["stripes_verified_per_frame"]=1
        p.write_text(json.dumps(o))
        with self.assertRaises(ValueError):publish(self.src,self.dst)
        self.assertFalse(self.dst.exists())

    def test_existing_target_never_overwritten(self):
        self.dst.mkdir()
        keep=self.dst/"keep"
        keep.write_text("safe")
        with self.assertRaises(ValueError):publish(self.src,self.dst)
        self.assertEqual(keep.read_text(),"safe")

if __name__=="__main__":unittest.main()
