"""Generated-only alpha analyzer fixtures; not emulator screenshots."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw

from tools.foj_stage265_generated_blend_sd import (
    ALPHAS, make_warm_dds, install_blend
)
from tools.foj_stage265_gpu_blend_check import (
    PROBES, blended_rgb, inspect,verify
)
from tools.foj_stage260_generated_gpu_sd import COLORS


def make_frame(path:Path,case:str,*,wrong_order=False,
               no_blend=False,missing_rear=False,
               swapped=False,background=(54,31,59)):
    im=Image.new("RGB",(1280,720),background)
    draw=ImageDraw.Draw(im)
    alpha=ALPHAS[case]
    composite=blended_rgb(alpha)
    rear=tuple(COLORS[1][:3])
    if missing_rear: composite=tuple(COLORS[0][:3])
    if wrong_order: composite=rear
    if no_blend: composite=tuple(COLORS[0][:3])
    if swapped: composite=rear
    for probe,(x,y) in PROBES.items():
        color=rear if probe=="rear_only" else composite
        if swapped and probe=="rear_only":color=tuple(COLORS[0][:3])
        draw.rectangle((x-10,y-10,x+10,y+10),fill=color)
    im.save(path)


def make_pair(root:Path,case:str,**bad):
    folder=root/case
    folder.mkdir()
    make_frame(folder/"gpu-initial.png",case,**bad)
    make_frame(folder/"gpu-later.png",case,
               background=(112,145,110),**bad)


class BlendTests(unittest.TestCase):
    def test_generated_dds_retains_rgb_and_changes_only_alpha(self):
        assert ALPHAS=={"clear":0,"half":128,"solid":255}
        src=make_warm_dds("solid")
        for case,alpha in ALPHAS.items():
            payload=make_warm_dds(case)
            self.assertEqual(len(payload),128+64*64*4)
            self.assertEqual(payload[:128],src[:128])
            for i in (0,32,1000,4095):
                pos=128+4*i
                self.assertEqual(payload[pos:pos+3],src[pos:pos+3])
                self.assertEqual(payload[pos+3],alpha)

    def test_intermediate_reference_rgb(self):
        self.assertEqual(blended_rgb(0),tuple(COLORS[1][:3]))
        self.assertEqual(blended_rgb(128),(127,128,123))
        self.assertEqual(blended_rgb(255),tuple(COLORS[0][:3]))

    def test_three_case_positive_counterfactual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for case in ALPHAS: make_pair(root,case)
            result=verify(root)
            self.assertEqual(result["actual_neixum_guest_frames_verified"],6)
            self.assertTrue(result["source_over_alpha_0_128_255"])
            self.assertFalse(result["original_ps3_assets_used"])

    def test_wrong_draw_order_or_disabled_blend_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,bad in (
                ("wrong_order",{"wrong_order":True}),
                ("no_blend",{"no_blend":True}),
                ("missing_rear",{"missing_rear":True}),
                ("swapped",{"swapped":True}),
            ):
                path=root/(name+".png")
                make_frame(path,"half",**bad)
                with self.subTest(bad=name),self.assertRaises(ValueError):
                    inspect(path,"half")

    def test_negative_frame_missing_or_duplicate_background(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for case in ALPHAS:make_pair(root,case)
            (root/"half"/"gpu-later.png").unlink()
            with self.assertRaises(OSError): verify(root)
            data=(root/"half"/"gpu-initial.png").read_bytes()
            (root/"half"/"gpu-later.png").write_bytes(data)
            with self.assertRaises(ValueError): verify(root)

    def test_missing_unexpected_or_reused_sd_root_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"private"
            root.mkdir()
            (root/"never-overwrite").write_bytes(b"user bytes")
            with self.assertRaises(ValueError):
                install_blend(root,Path(tmp)/"shaders","half")
            with self.assertRaises(ValueError):
                install_blend(Path(tmp)/"other",Path(tmp)/"shaders","bogus")
            self.assertEqual((root/"never-overwrite").read_bytes(),b"user bytes")

    def test_wrong_case_fails_even_if_correct_opaque(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"wrong.png"
            make_frame(p,"solid")
            with self.assertRaises(ValueError):
                inspect(p,"half")


if __name__=="__main__":
    unittest.main()
