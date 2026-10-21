"""Stage307 host images are MOCKS and never count as NeXium evidence."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from tools.foj_stage293_converted_dds_guest import _origin,_attestation
from tools.foj_stage306_patterned_uv_guest import MARKER as BASE_MARKER
from tools.foj_stage306_patterned_uv_guest import MARKER_BYTES as BASE_BYTES
from tools.foj_stage306_patterned_uv_guest import RECEIPT as BASE_RECEIPT
from tools.foj_stage306_patterned_uv_guest import audit as stage306_audit
from tools.foj_stage307_filter_gpu_compare import (
    COLORS,EDGES,MARKER,EXPECTED,PUBLIC,audit,compare,publish
)

def mock(source:Path,mode:str):
    bridge=source/"bridge"
    bridge.mkdir(parents=True)
    for name,value in (
        ("generated-input.json",_origin()),
        ("dds-before.json",_attestation("before")),
        ("dds-after.json",_attestation("after")),
    ):
        (bridge/name).write_text(json.dumps(value))
    (bridge/BASE_MARKER).write_bytes(BASE_BYTES)
    (bridge/MARKER).write_bytes(EXPECTED[mode])
    (bridge/"guest.log").write_text("MOCK ONLY; not guest evidence")
    (source/"nexium-archive.sha256").write_text("a"*64+"  /tmp/nexium.tar.gz\n")
    for filename,background in (("gpu-initial.png",(15,50,68)),
                                ("gpu-later.png",(65,32,51))):
        img=Image.new("RGB",(1280,720),background)
        draw=ImageDraw.Draw(img)
        for side,start in (("left",256),("right",640)):
            for band,color in enumerate(COLORS[side]):
                draw.rectangle((start+96*band,180,
                                start+96*(band+1)-1,539),fill=color)
        if mode=="linear":
            for side,locations in EDGES.items():
                for band,x in enumerate(locations):
                    a,b=COLORS[side][band:band+2]
                    for xx,weight in ((x-1,1/6),(x,5/6)):
                        color=tuple(round(a[k]*(1-weight)+b[k]*weight)
                                    for k in range(3))
                        draw.line(((xx,390),(xx,415)),fill=color)
        img.save(bridge/filename)
    (bridge/BASE_RECEIPT).write_text(json.dumps(stage306_audit(bridge)))

class FilterEvidenceMocks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.n=self.root/"nearest"
        self.l=self.root/"linear"
        mock(self.n,"nearest")
        mock(self.l,"linear")
        self.out_n=self.root/"out-nearest"
        self.out_l=self.root/"out-linear"

    def test_both_modes_preserve_eight_generated_bands(self):
        for p,mode in ((self.n,"nearest"),(self.l,"linear")):
            self.assertTrue(audit(p/"bridge",mode)["stage306_eight_bands_verified"])

    def test_genuine_filter_difference_contract_on_synthetic_mock(self):
        publish(self.n,self.out_n,"nearest")
        publish(self.l,self.out_l,"linear")
        result=compare(self.out_n,self.out_l)
        self.assertTrue(result["within_page_linear_transition_observed"])
        self.assertEqual(result["guest_frames_audited"],4)
        self.assertFalse(result["inter_page_bilinear_reconstruction_verified"])
        self.assertGreaterEqual(result["per_phase_transition"]
                                ["gpu-initial.png"]["intermediate_differences"],8)

    def test_neixum_viewport_inset_still_requires_all_six_real_transitions(self):
        # Host-generated regression models the *observed* insets of a
        # windowed 1280px NeXium capture (270..1009), not the ideal
        # nominal clip-space rectangle 256..1023. Both modes must pass
        # only when nearest is sharp and linear blends at each measured
        # RGB step. These mocks are NEVER real guest evidence.
        for source,mode in ((self.n,"nearest"),(self.l,"linear")):
            for filename,bg in (("gpu-initial.png",(15,50,68)),
                                ("gpu-later.png",(65,32,51))):
                image=Image.new("RGB",(1280,720),bg)
                pen=ImageDraw.Draw(image)
                borders=[round(270+i*740/8) for i in range(9)]
                colors=(*COLORS["left"],*COLORS["right"])
                for i,color in enumerate(colors):
                    pen.rectangle((borders[i],180,borders[i+1]-1,539),
                                  fill=color)
                if mode=="linear":
                    for i in (1,2,3,5,6,7):
                        boundary=borders[i]
                        before,after=colors[i-1],colors[i]
                        for x,weight in ((boundary-1,1/6),
                                         (boundary,5/6)):
                            mixed=tuple(round(before[k]*(1-weight)+
                                              after[k]*weight)
                                        for k in range(3))
                            pen.line(((x,390),(x,415)),fill=mixed)
                image.save(source/"bridge"/filename)
            # Source generation changed the synthetic screenshot but
            # not any real guest file, public provenance or game byte.
            from tools.foj_stage306_patterned_uv_guest import audit as base_audit
            self.assertEqual(base_audit(source/"bridge")[
                "interpolated_uv_bands_verified"],8)
        publish(self.n,self.out_n,"nearest")
        publish(self.l,self.out_l,"linear")
        out=compare(self.out_n,self.out_l)
        self.assertEqual(out["per_phase_transition"][
            "gpu-initial.png"]["intermediate_differences"],12)

    def test_identical_filters_refused(self):
        publish(self.n,self.out_n,"nearest")
        publish(self.l,self.out_l,"linear")
        for filename in ("gpu-initial.png","gpu-later.png"):
            (self.out_l/"bridge"/filename).write_bytes(
                (self.out_n/"bridge"/filename).read_bytes())
        with self.assertRaises(ValueError):compare(self.out_n,self.out_l)

    def test_wrong_mode_witness_refused(self):
        with self.assertRaises(ValueError):audit(self.n/"bridge","linear")
        (self.l/"bridge"/MARKER).write_bytes(EXPECTED["nearest"])
        with self.assertRaises(ValueError):audit(self.l/"bridge","linear")

    def test_linear_result_outside_palette_bounds_refused(self):
        publish(self.n,self.out_n,"nearest")
        publish(self.l,self.out_l,"linear")
        path=self.out_l/"bridge"/"gpu-initial.png"
        with Image.open(path) as im:changed=im.convert("RGB")
        changed.putpixel((351,400),(17,210,64))
        changed.save(path)
        with self.assertRaises(ValueError):compare(self.out_n,self.out_l)

    def test_nearest_transition_wrong_pixel_refused(self):
        publish(self.n,self.out_n,"nearest")
        publish(self.l,self.out_l,"linear")
        path=self.out_n/"bridge"/"gpu-initial.png"
        with Image.open(path) as im:changed=im.convert("RGB")
        changed.putpixel((352,400),(0,0,0))
        changed.save(path)
        with self.assertRaises(ValueError):compare(self.out_n,self.out_l)

    def test_bad_eight_band_geometry_also_refused(self):
        path=self.n/"bridge"/"gpu-initial.png"
        with Image.open(path) as im:changed=im.convert("RGB")
        ImageDraw.Draw(changed).rectangle((300,396,308,404),fill=(20,20,20))
        changed.save(path)
        with self.assertRaises(ValueError):audit(self.n/"bridge","nearest")

    def test_extra_original_dds_cannot_be_published(self):
        (self.n/"bridge"/"original_asset.dds").write_bytes(b"private")
        with self.assertRaises(ValueError):publish(self.n,self.out_n,"nearest")
        self.assertFalse(self.out_n.exists())

    def test_symbolic_link_png_cannot_be_published(self):
        p=self.l/"bridge"/"gpu-later.png"
        p.unlink()
        p.symlink_to(self.l/"bridge"/"gpu-initial.png")
        with self.assertRaises(ValueError):publish(self.l,self.out_l,"linear")

    def test_raw_guest_log_stripped_and_nine_public_files(self):
        data=publish(self.n,self.out_n,"nearest")
        self.assertEqual(data["public_files"],9)
        self.assertEqual(len(PUBLIC),9)
        self.assertFalse((self.out_n/"bridge"/"guest.log").exists())

    def test_preexisting_folder_not_overwritten(self):
        self.out_n.mkdir()
        p=self.out_n/"keep"
        p.write_text("important")
        with self.assertRaises(ValueError):publish(self.n,self.out_n,"nearest")
        self.assertEqual(p.read_text(),"important")

    def test_original_game_or_hardware_not_attested(self):
        item=audit(self.l/"bridge","linear")
        self.assertFalse(item["original_ps3_assets_used"])
        self.assertFalse(item["physical_switch_verified"])

if __name__=="__main__":
    unittest.main()
