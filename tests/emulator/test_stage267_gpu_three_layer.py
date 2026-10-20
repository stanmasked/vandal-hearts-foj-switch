"""Stage267 host synthetic fixture guards, not real NeXium frame evidence."""
from pathlib import Path
import struct
import tempfile
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage267_generated_multiblend_sd import (
    CASES, COLORS, DEPTHS, expected_rgb, generated_three_layer_mesh,
    generated_three_layer_materials, install_three_layer,
)
from tools.foj_stage267_gpu_three_layer_check import (
    inspect, verify, PROBES,
)
from tools.foj_stage266_transparency_order import COOL


def synthetic_image(path: Path, case: str, background=(54,31,59),
                    wrong_color=None, rear_color=COOL) -> None:
    image=Image.new("RGB",(1280,720),background)
    draw=ImageDraw.Draw(image)
    for probe,(x,y) in PROBES.items():
        target=rear_color if probe=="rear_only" else (
            expected_rgb(case) if wrong_color is None else wrong_color)
        draw.rectangle((x-9,y-9,x+9,y+9),fill=target)
    image.save(path)


def synthetic_pair(root: Path, case: str, **kwargs) -> None:
    path=root/case
    path.mkdir(parents=True)
    synthetic_image(path/"gpu-initial.png",case,**kwargs)
    synthetic_image(path/"gpu-later.png",case,background=(112,145,110),**kwargs)


class ThreeLayerTests(unittest.TestCase):
    def test_three_material_actor_binary_header_and_three_draw_ranges(self):
        raw=generated_three_layer_mesh()
        self.assertEqual(raw[:8],b"FOJRM001")
        self.assertEqual(len(raw),28+32+3*8+9*76)
        self.assertEqual(struct.unpack_from("<IIIII",raw,8),(1,1,9,3,0))
        self.assertEqual(struct.unpack_from("<IIIIII",raw,60),(0,3,3,3,6,3))
        self.assertEqual(generated_three_layer_materials(),
            b"FOJMAT01"+struct.pack("<IIIII",3,3,0,1,2))
        for i, name in enumerate(("violet","warm","cool")):
            self.assertAlmostEqual(struct.unpack_from("<f",raw,84+76*3*i+8)[0],
                                   DEPTHS[name], places=6)

    def test_three_independent_color_controls(self):
        self.assertEqual(CASES,{"both-half":(128,128),
                                "no-middle":(128,0),"no-near":(0,128)})
        self.assertEqual(expected_rgb("both-half"),(111,100,162))
        self.assertEqual(expected_rgb("no-middle"),(59,137,210))
        self.assertEqual(expected_rgb("no-near"),(127,128,123))
        self.assertEqual(set(COLORS),{"violet","warm","cool"})
        with self.assertRaises(ValueError):expected_rgb("unsupported")

    def test_synthetic_images_only_prove_classifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for case in CASES: synthetic_pair(root,case)
            proof=verify(root)
            self.assertEqual(proof["screenshot_files_inspected"],6)
            self.assertFalse(proof["physical_switch_verified"])
            self.assertIn("requires separate",proof["actual_guest_capture_provenance"])

    def test_missing_or_duplicate_frame_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for case in CASES: synthetic_pair(root,case)
            first=root/"both-half"/"gpu-initial.png"
            second=root/"both-half"/"gpu-later.png"
            second.write_bytes(first.read_bytes())
            with self.assertRaises(ValueError): verify(root)
            second.unlink()
            with self.assertRaises(OSError): verify(root)

    def test_wrong_blend_reversed_order_or_missing_rear_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for label,color,rear in (
                ("blend-disabled",(96,72,201),COOL),
                ("wrong-compositing",(111,100,100),COOL),
                ("missing-rear",(111,100,162),(54,31,59)),
                ("only-middle",(127,128,123),COOL),
            ):
                path=root/(label+".png")
                synthetic_image(path,"both-half",wrong_color=color,rear_color=rear)
                with self.subTest(label=label),self.assertRaises(ValueError):
                    inspect(path,"both-half")

    def test_root_safety_no_existing_private_data_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"already-exists"
            root.mkdir()
            (root/"sentinel").write_bytes(b"private")
            with self.assertRaises(ValueError):
                install_three_layer(root,Path(tmp)/"missing-shaders","both-half")
            self.assertEqual((root/"sentinel").read_bytes(),b"private")

    def test_bad_case_does_not_create_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"never-created"
            with self.assertRaises(ValueError):
                install_three_layer(root,Path(tmp)/"missing-shaders","invalid")
            self.assertFalse(root.exists())


if __name__=="__main__":
    unittest.main()
