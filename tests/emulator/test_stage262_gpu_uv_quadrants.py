"""Stage262 UNIT fixtures: fake PIL polygons test the verifier but NEVER
qualify as real NeXium framebuffer proof. All binary texture pixels invented.
"""
from pathlib import Path
import struct
import tempfile
import unittest
from PIL import Image

from tools.foj_stage262_generated_uv_sd import (
    PALETTES,quadrant_dds,install_quadrants
)
from tools.foj_stage262_gpu_uv_check import (
    UV_SITES,screen_for_uv,inspect,audit
)
from tools.foj_stage261_projection_audit import (
    TRIANGLES,projected_vertices
)


def reference_frame(path, *, no_material=None, u_flip=False, v_flip=False,
                    flat=False,swap=False,background=(54,31,59)):
    image=Image.new("RGB",(1280,720),background)
    px=image.load()
    for name in ("warm","cool"):
        if name==no_material:
            continue
        xy=projected_vertices(1280,720,TRIANGLES[name])
        colors=PALETTES["cool" if (swap and name=="warm") else
                        "warm" if (swap and name=="cool") else name]
        (ax,ay),(bx,by),(cx,cy)=xy
        den=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
        for y in range(min(ay,by,cy),max(ay,by,cy)+1):
            for x in range(min(ax,bx,cx),max(ax,bx,cx)+1):
                right=((x-ax)*(cy-ay)-(y-ay)*(cx-ax))/den
                top=((bx-ax)*(y-ay)-(by-ay)*(x-ax))/den
                left=1-right-top
                if min(left,right,top)<0:
                    continue
                u=right+top/2
                v=1-top
                if u_flip and name=="warm":u=1-u
                if v_flip and name=="warm":v=1-v
                idx=0 if flat else (2 if v>=.5 else 0)+(1 if u>=.5 else 0)
                px[x,y]=colors[idx][:3]
    image.save(path)


class GeneratedQuadrants(unittest.TestCase):
    def test_canonical_dds_pixels(self):
        for name,colors in PALETTES.items():
            dds=quadrant_dds(colors)
            self.assertEqual(len(dds),128+64*64*4)
            self.assertEqual(dds[:4],b"DDS ")
            self.assertEqual(struct.unpack_from("<II",dds,12),(64,64))
            for x,y,idx in ((5,5,0),(58,5,1),(5,58,2),(58,58,3)):
                at=128+4*(y*64+x)
                self.assertEqual(dds[at:at+4],bytes(colors[idx]))
            self.assertEqual(len(set(colors)),4)
            self.assertTrue(all(c[3]==255 for c in colors))

    def test_no_existing_private_directory_can_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"private"
            folder.mkdir()
            (folder/"secret").write_bytes(b"user asset")
            with self.assertRaises(ValueError):
                install_quadrants(folder,Path(tmp)/"fake-shaders")
            self.assertEqual((folder/"secret").read_bytes(),b"user asset")

    def test_independent_uv_projection_points(self):
        xy=projected_vertices(1280,720,TRIANGLES["warm"])
        points=[screen_for_uv(q,xy) for q in UV_SITES]
        self.assertEqual(len(points),4)
        self.assertLess(points[0][0],points[1][0])
        self.assertLess(points[2][0],points[3][0])
        self.assertLess(points[0][1],points[2][1])
        with self.assertRaises(ValueError):
            screen_for_uv((0,0),xy)

    def test_positive_reference_two_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            reference_frame(root/"gpu-initial.png")
            reference_frame(root/"gpu-later.png",background=(112,145,110))
            receipt=audit(root)
            self.assertEqual(receipt["frame_count"],2)
            self.assertTrue(receipt["eight_distinct_uv_quadrants_verified"])
            for material in ("warm","cool"):
                for quadrant in ("top_left","top_right","bottom_left","bottom_right"):
                    self.assertGreater(
                        receipt["first"][material]["interpolated_uv_samples"]
                        [quadrant]["matching_samples"],32)

    def test_mirror_swap_missing_and_flat_atlas_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"bad.png"
            for kwargs in (
                {"u_flip":True},{"v_flip":True},{"swap":True},
                {"flat":True},{"no_material":"warm"},{"no_material":"cool"}
            ):
                with self.subTest(kwargs=kwargs):
                    reference_frame(target,**kwargs)
                    with self.assertRaises(ValueError):
                        inspect(target)

    def test_missing_or_duplicate_guest_capture_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            reference_frame(root/"gpu-initial.png")
            with self.assertRaises(OSError):
                audit(root)
            reference_frame(root/"gpu-later.png")
            with self.assertRaises(ValueError):
                audit(root)


if __name__=="__main__":
    unittest.main()
