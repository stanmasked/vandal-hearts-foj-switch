"""Stage260 guards: independent synthetic images never count as guest evidence."""
from pathlib import Path
import struct
import tempfile
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage260_generated_gpu_sd import (
    generated_geometry, generated_materials, generated_dds, COLORS, install_generated
)
from tools.foj_stage260_gpu_guest_check import inspect, verify


class GeneratorTests(unittest.TestCase):
    def test_invented_interchange_header_and_two_sections(self):
        m=generated_geometry()
        t=generated_materials()
        self.assertEqual(len(m),28+32+16+6*76)
        self.assertEqual(m[:8],b"FOJRM001")
        self.assertEqual(struct.unpack_from("<III",m,12),(1,6,2))
        self.assertEqual(struct.unpack_from("<IIII",m,60),(0,3,3,3))
        self.assertEqual(t,b"FOJMAT01"+struct.pack("<IIII",2,2,0,1))
        for i in range(6):
            xyz=struct.unpack_from("<fff",m,76+76*i)
            self.assertTrue(all(-1 <= v <= 1 for v in xyz))
            self.assertEqual(struct.unpack_from("<I",m,76+76*i+32)[0],1)

    def test_dds_are_byte_exact_rgba_and_not_source_assets(self):
        for color in COLORS:
            blob=generated_dds(color)
            self.assertEqual(len(blob),128+64*64*4)
            self.assertEqual(blob[:4],b"DDS ")
            self.assertEqual(struct.unpack_from("<II",blob,12),(64,64))
            self.assertEqual(blob[128:132],bytes(color))
            self.assertEqual(blob[-4:],bytes(color))

    def test_existing_sd_directory_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"private-files"
            root.mkdir()
            (root/"sentinel").write_text("private")
            with self.assertRaises(ValueError):
                install_generated(root,Path(tmp)/"shaders")
            self.assertEqual((root/"sentinel").read_text(),"private")


def synthetic_frame(path, warm=True, cool=True, reversed=False):
    image=Image.new("RGB",(1280,720),(54,31,59))
    draw=ImageDraw.Draw(image)
    warm_color=(232,55,28)
    cool_color=(21,202,219)
    if reversed:
        warm_color,cool_color=cool_color,warm_color
    if warm:
        draw.polygon(((390,520),(625,520),(500,210)),fill=warm_color)
    if cool:
        draw.polygon(((655,520),(885,520),(760,210)),fill=cool_color)
    image.save(path)


class ScreenshotTests(unittest.TestCase):
    def test_synthetic_fixture_is_only_classifier_unit_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for name in ("gpu-initial.png","gpu-later.png"):
                synthetic_frame(folder/name)
            got=verify(folder)
            self.assertEqual(got["actual_emulator_screenshots_verified"],2)
            self.assertTrue(got["ordered_gpu_material_mapping_verified"])
            self.assertFalse(got["original_ps3_assets_loaded"])

    def test_blank_one_material_and_reversed_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for warm,cool,reversed in (
                (False,False,False),(True,False,False),
                (False,True,False),(True,True,True)
            ):
                synthetic_frame(root/"invalid.png",warm,cool,reversed)
                with self.assertRaises(ValueError):
                    inspect(root/"invalid.png")

    def test_missing_image_is_not_silently_inferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            synthetic_frame(root/"gpu-initial.png")
            with self.assertRaises(OSError):
                verify(root)


if __name__=="__main__":
    unittest.main()
