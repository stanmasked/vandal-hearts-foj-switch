"""Generated-only unit/negative depth controls; no unit image is GPU proof."""
from pathlib import Path
import struct
import tempfile
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage263_generated_depth_sd import (
    TRIANGLES,PROBES,overlap_mesh,install_depth
)
from tools.foj_stage263_gpu_depth_check import inspect,verify
from tools.foj_stage260_generated_gpu_sd import COLORS
from tools.foj_stage261_projection_audit import projected_vertices


def fixture(path:Path,near:str,*,correct_depth:bool=True,
            missing:str|None=None,bg=(54,31,59)):
    img=Image.new("RGB",(1280,720),bg)
    # Without a depth target, draw order warm->cool decides central pixel.
    materials=("cool","warm") if near=="warm" and correct_depth else (
              ("warm","cool") if near=="cool" and correct_depth else
              ("warm","cool"))
    for material in materials:
        if material==missing:
            continue
        triangle=projected_vertices(1280,720,TRIANGLES[material])
        col=COLORS[0 if material=="warm" else 1]
        ImageDraw.Draw(img).polygon(triangle,fill=col[:3])
    img.save(path)


def make_pair(root:Path,near:str,**kw):
    out=root/near
    out.mkdir(parents=True)
    fixture(out/"gpu-initial.png",near,**kw)
    fixture(out/"gpu-later.png",near,bg=(112,145,110),**{
        k:v for k,v in kw.items() if k!="bg"
    })


class GeneratedDepthTests(unittest.TestCase):
    def test_source_is_two_triangle_fojrm_with_reversible_depth(self):
        for near in ("warm","cool"):
            m=overlap_mesh(near)
            self.assertEqual(m[:8],b"FOJRM001")
            self.assertEqual(len(m),28+32+2*8+6*76)
            z0=struct.unpack_from("<f",m,76+8)[0]
            z1=struct.unpack_from("<f",m,76+3*76+8)[0]
            self.assertTrue((z0>z1)==(near=="warm"))
            for idx,tri in enumerate(("warm","cool")):
                for j,xy in enumerate(TRIANGLES[tri]):
                    pos=76+76*(idx*3+j)
                    actual=struct.unpack_from("<fff",m,pos)
                    self.assertAlmostEqual(actual[0],xy[0],places=5)
                    self.assertAlmostEqual(actual[1],xy[1],places=5)
        with self.assertRaises(ValueError):
            overlap_mesh("not-material")

    def test_probe_geometry(self):
        xy={key:projected_vertices(1280,720,value)
            for key,value in TRIANGLES.items()}
        def inside(point,triangle):
            (ax,ay),(bx,by),(cx,cy)=triangle
            x,y=point
            det=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
            b=((x-ax)*(cy-ay)-(y-ay)*(cx-ax))/det
            c=((bx-ax)*(y-ay)-(by-ay)*(x-ax))/det
            return min(1-b-c,b,c)>.07
        self.assertTrue(inside(PROBES["overlap"],xy["warm"]))
        self.assertTrue(inside(PROBES["overlap"],xy["cool"]))
        self.assertTrue(inside(PROBES["warm_only"],xy["warm"]))
        self.assertFalse(inside(PROBES["warm_only"],xy["cool"]))
        self.assertTrue(inside(PROBES["cool_only"],xy["cool"]))
        self.assertFalse(inside(PROBES["cool_only"],xy["warm"]))

    def test_correct_depth_both_draw_orders(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            make_pair(root,"warm")
            make_pair(root,"cool")
            data=verify(root)
            self.assertTrue(data["draw_order_independent_occlusion"])
            self.assertEqual(data["actual_guest_frames_verified"],4)
            self.assertFalse(data["original_ps3_asset_loaded"])

    def test_no_depth_buffer_cannot_pass_first_draw_nearer(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            make_pair(root,"warm",correct_depth=False)
            make_pair(root,"cool")
            with self.assertRaises(ValueError):
                verify(root)

    def test_opposite_depth_wrong_winner_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            make_pair(root,"warm")
            make_pair(root,"cool")
            fixture(root/"cool"/"gpu-initial.png","warm")
            with self.assertRaises(ValueError):
                verify(root)

    def test_missing_far_wing_and_missing_frame_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            make_pair(root,"warm",missing="cool")
            make_pair(root,"cool")
            with self.assertRaises(ValueError):
                verify(root)
            make_pair(Path(temp)/"second","warm")
            (Path(temp)/"second"/"warm"/"gpu-later.png").unlink()
            with self.assertRaises(OSError):
                verify(Path(temp)/"second")

    def test_duplicate_frames_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            make_pair(root,"warm")
            make_pair(root,"cool")
            for material in ("warm","cool"):
                (root/material/"gpu-later.png").write_bytes(
                    (root/material/"gpu-initial.png").read_bytes()
                )
            with self.assertRaises(ValueError):
                verify(root)

    def test_existing_user_directory_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"private"
            root.mkdir()
            (root/"sentinel").write_bytes(b"user data")
            with self.assertRaises(ValueError):
                install_depth(root,Path(temp)/"shaders","warm")
            self.assertEqual((root/"sentinel").read_bytes(),b"user data")


if __name__=="__main__":
    unittest.main()
