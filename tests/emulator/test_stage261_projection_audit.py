"""Negative/positive tests of Stage261 calibration. These generated PIL
images are ONLY classifier unit fixtures, never guest runtime evidence."""
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage261_projection_audit import (
    TRIANGLES, projected_vertices, inspect, audit,
)


def picture(path:Path, *, shift=0, ratio=1., missing=None, swapped=False,
            background=(54,31,59)):
    image=Image.new("RGB",(1280,720),background)
    colors={"warm":(232,55,28),"cool":(21,202,219)}
    if swapped:
        colors={"warm":(21,202,219),"cool":(232,55,28)}
    for name,tri in TRIANGLES.items():
        if name==missing:
            continue
        verts=projected_vertices(1280,720,tri)
        center_x=sum(x for x,_ in verts)/3.
        center_y=sum(y for _,y in verts)/3.
        coords=[(round(center_x+ratio*(x-center_x)+shift),
                 round(center_y+ratio*(y-center_y))) for x,y in verts]
        ImageDraw.Draw(image).polygon(coords,fill=colors[name])
    image.save(path)


class CalibrationTests(unittest.TestCase):
    def test_independent_camera_pixel_coordinates(self):
        self.assertEqual(projected_vertices(1280,720,TRIANGLES["warm"]),
                         ((380,487),(631,487),(507,166)))
        self.assertEqual(projected_vertices(1280,720,TRIANGLES["cool"]),
                         ((649,487),(900,487),(773,166)))
        with self.assertRaises(ValueError):
            projected_vertices(640,360,TRIANGLES["warm"])

    def test_reference_footprint_can_be_confirmed(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"valid.png"
            picture(path)
            found=inspect(path)
            for name in TRIANGLES:
                self.assertGreater(found[name]["silhouette_iou"],.98)

    def test_missing_swapped_scaled_or_shifted_geometry_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"invalid.png"
            for opts in (
                {"missing":"warm"},{"missing":"cool"},
                {"swapped":True},{"ratio":.55},{"shift":70}
            ):
                picture(path,**opts)
                with self.subTest(opts=opts), self.assertRaises(ValueError):
                    inspect(path)

    def test_distinct_background_frames_required(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            picture(root/"gpu-initial.png")
            picture(root/"gpu-later.png",background=(112,145,110))
            outcome=audit(root)
            self.assertEqual(outcome["frame_count"],2)
            self.assertTrue(outcome["geometry_projection_checked"])
            picture(root/"gpu-later.png")
            with self.assertRaises(ValueError):
                audit(root)

    def test_missing_second_frame_cannot_be_inferred(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            picture(root/"gpu-initial.png")
            with self.assertRaises(OSError):
                audit(root)


if __name__=="__main__":
    unittest.main()
