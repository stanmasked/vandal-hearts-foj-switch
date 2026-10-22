"""Stage316 synthetic screenshot negatives; NEVER real NeXium evidence."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage316_corner_gpu_guest import (
    MARKER,MARKER_BYTES,RECEIPT,PUBLIC,_frame,audit,publish,
)
def fake_frame(path:Path,bg:tuple[int,int,int]):
    im=Image.new("RGB",(1280,720),bg)
    width,height=561,331
    data=bytearray(width*height*3)
    for y in range(height):
        ty=y/(height-1)
        for x in range(width):
            tx=x/(width-1)
            n=(y*width+x)*3
            data[n]=round(255*((1-tx)*(1-ty)+tx*ty))
            data[n+1]=round(255*tx)
            data[n+2]=round(255*ty)
    patch=Image.frombytes("RGB",(width,height),bytes(data))
    im.paste(patch,(360,181))
    im.save(path)

def mock(root:Path):
    bridge=root/"bridge"
    bridge.mkdir(parents=True)
    for name,data in (
        ("generated-input.json",_origin()),
        ("dds-before.json",_attestation("before")),
        ("dds-after.json",_attestation("after")),
    ):
        (bridge/name).write_text(json.dumps(data))
    (bridge/MARKER).write_bytes(MARKER_BYTES)
    (bridge/"guest.log").write_text("host mock only - never a guest frame")
    (root/"nexium-archive.sha256").write_text(
        "b"*64+"  /tmp/nexium.tar.gz\n"
    )
    fake_frame(bridge/"gpu-initial.png",(15,45,68))
    fake_frame(bridge/"gpu-later.png",(72,23,40))
    (bridge/RECEIPT).write_text(json.dumps(audit(bridge)))
    return bridge

class Stage316HostOnlyNegatives(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.source=self.root/"source"
        self.source.mkdir()
        self.bridge=mock(self.source)
    def corrupt(self,name:str,rect,color):
        path=self.bridge/name
        with Image.open(path) as read:
            image=read.convert("RGB")
        ImageDraw.Draw(image).rectangle(rect,fill=color)
        image.save(path)
    def test_host_mock_shape_not_gpu_proof(self):
        result=audit(self.bridge)
        self.assertTrue(result["generated_only"])
        self.assertEqual(result["real_neixum_frames_verified"],2)
        self.assertEqual(result["corners_verified_per_frame"],4)
        self.assertFalse(result["physical_switch_verified"])
        self.assertFalse(result["automatic_cross_texture_bilinear_verified"])
        for frame in result["per_frame_probes"].values():
            self.assertEqual(frame["center_x"],640)
            self.assertEqual(frame["center_y"],346)
            self.assertGreaterEqual(frame["midpoint_matching_pixels"],22)
            self.assertTrue(all(v>=20 for v in
                                frame["independent_corner_color_regions"].values()))
    def test_false_constant_midpoint_bar(self):
        # A host-painted center can match 128/128/128 but it is not a
        # physically varying bilinear surface in either direction.
        self.corrupt("gpu-initial.png",(627,333,653,359),(128,128,128))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_missing_2d_center(self):
        self.corrupt("gpu-initial.png",(604,308,676,387),(2,2,2))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_missing_northeast(self):
        self.corrupt("gpu-later.png",(740,181,920,330),(1,1,1))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_horizontal_gradient_missing(self):
        self.corrupt("gpu-initial.png",(566,300,718,398),(128,128,128))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_vertical_gradient_missing(self):
        self.corrupt("gpu-initial.png",(558,279,722,412),(128,128,128))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_wrong_guest_receipt(self):
        (self.bridge/MARKER).write_bytes(b"fake")
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_wrong_source_attestation(self):
        path=self.bridge/"dds-after.json"
        data=json.loads(path.read_text())
        data["generated_only"]=False
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_one_gpu_clear_phase(self):
        (self.bridge/"gpu-later.png").write_bytes(
            (self.bridge/"gpu-initial.png").read_bytes())
        with self.assertRaises(ValueError):audit(self.bridge)
    def test_public_allowlist_and_no_guest_logs(self):
        output=self.root/"public"
        result=publish(self.source,output)
        self.assertEqual(result["public_files"],8)
        self.assertFalse((output/"bridge"/"guest.log").exists())
        self.assertEqual(len(PUBLIC),8)
    def test_forged_saved_receipt_rejected(self):
        receipt=self.bridge/RECEIPT
        data=json.loads(receipt.read_text())
        data["real_neixum_frames_verified"]=3
        receipt.write_text(json.dumps(data))
        with self.assertRaises(ValueError):publish(self.source,self.root/"out")
    def test_spurious_file_rejected(self):
        (self.source/"private-ps3.bin").write_bytes(b"private")
        with self.assertRaises(ValueError):publish(self.source,self.root/"out")

if __name__=="__main__":
    unittest.main()
