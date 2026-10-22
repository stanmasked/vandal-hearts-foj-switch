"""Stage312 fabricated image tests: never claim these frames came from NeXium."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage312_horizontal_gpu_guest import (
    MARKER,MARKER_BYTES,RECEIPT,PAIRS565,X_CENTERS,rgb565,
    _frame,audit,publish,PUBLIC
)

def mock(root:Path):
    bridge=root/"bridge"
    bridge.mkdir(parents=True)
    for name,obj in (("generated-input.json",_origin()),
                     ("dds-before.json",_attestation("before")),
                     ("dds-after.json",_attestation("after"))):
        (bridge/name).write_text(json.dumps(obj))
    (bridge/MARKER).write_bytes(MARKER_BYTES)
    (bridge/"guest.log").write_text("mock only; not actual guest GPU data")
    (root/"nexium-archive.sha256").write_text("b"*64+"  /tmp/nexium.tar.gz\n")
    for filename,bg in (("gpu-initial.png",(15,50,68)),
                        ("gpu-later.png",(65,32,51))):
        im=Image.new("RGB",(1280,720),bg)
        d=ImageDraw.Draw(im)
        for i,x in enumerate(X_CENTERS):
            lo,hi=x-42,x+42
            top=rgb565(PAIRS565[0][i])
            bottom=rgb565(PAIRS565[1][i])
            d.rectangle((lo,180,hi,359),fill=top)
            d.rectangle((lo,360,hi,539),fill=bottom)
            for yy in range(341,380):
                t=(yy-341)/38
                mixed=tuple(round(top[k]*(1-t)+bottom[k]*t)
                            for k in range(3))
                d.line(((lo,yy),(hi,yy)),fill=mixed)
        im.save(bridge/filename)
    (bridge/RECEIPT).write_text(json.dumps(audit(bridge)))

class HorizontalGPUHostOnlyNegativeTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.src=self.root/"source"
        self.dst=self.root/"out"
        mock(self.src)
        self.bridge=self.src/"bridge"
    def corrupt(self,name,rect,color):
        p=self.bridge/name
        with Image.open(p) as f:im=f.convert("RGB")
        ImageDraw.Draw(im).rectangle(rect,fill=color)
        im.save(p)
    def test_all_eight_horizontal_seams(self):
        r=audit(self.bridge)
        self.assertEqual(r["column_color_pairs_per_frame"],8)
        self.assertEqual(r["real_neixum_guest_frames_verified"],2)
        for values in r["per_frame_pixel_probes"].values():
            self.assertEqual(len(values),24)
            self.assertTrue(all(v>=33 for k,v in values.items()
                                if k.endswith("_mixed")))
        self.assertFalse(r["independent_page_bilinear_reconstruction_verified"])
        self.assertFalse(r["physical_switch_verified"])
    def test_missing_upper_color(self):
        x=X_CENTERS[0]
        self.corrupt("gpu-initial.png",(x-5,275,x+5,285),(1,2,3))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_missing_lower_color(self):
        x=X_CENTERS[3]
        self.corrupt("gpu-later.png",(x-5,455,x+5,465),(1,2,3))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_clamped_midpoint(self):
        i=4;x=X_CENTERS[i]
        self.corrupt("gpu-initial.png",(x-5,351,x+5,369),
                     rgb565(PAIRS565[0][i]))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_missing_color_band(self):
        x=X_CENTERS[6]
        self.corrupt("gpu-initial.png",(x-5,260,x+5,480),(1,2,3))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_only_one_frame_phase(self):
        (self.bridge/"gpu-later.png").write_bytes(
            (self.bridge/"gpu-initial.png").read_bytes())
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_wrong_native_marker(self):
        (self.bridge/MARKER).write_bytes(b"fake success\n")
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_modified_generated_input(self):
        (self.bridge/"generated-input.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_modified_dds_after(self):
        (self.bridge/"dds-after.json").write_text("{}")
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_only_eight_public_files(self):
        result=publish(self.src,self.dst)
        self.assertEqual(result["public_files"],8)
        self.assertEqual(len(PUBLIC),8)
        self.assertFalse((self.dst/"bridge"/"guest.log").exists())
        self.assertEqual(audit(self.dst/"bridge"),audit(self.bridge))
    def test_owner_dds_leak_refused(self):
        (self.bridge/"original-game.dds").write_bytes(b"private")
        with self.assertRaises(ValueError):publish(self.src,self.dst)
        self.assertFalse(self.dst.exists())
    def test_symbolic_link_refused(self):
        p=self.bridge/"gpu-later.png"
        p.unlink()
        p.symlink_to(self.bridge/"gpu-initial.png")
        with self.assertRaises(ValueError):publish(self.src,self.dst)
    def test_stale_receipt_refused(self):
        p=self.bridge/RECEIPT
        r=json.loads(p.read_text())
        r["column_color_pairs_per_frame"]=0
        p.write_text(json.dumps(r))
        with self.assertRaises(ValueError):publish(self.src,self.dst)
    def test_destination_not_overwritten(self):
        self.dst.mkdir()
        (self.dst/"keep").write_text("already here")
        with self.assertRaises(ValueError):publish(self.src,self.dst)
        self.assertEqual((self.dst/"keep").read_text(),"already here")

if __name__=="__main__":
    unittest.main()
