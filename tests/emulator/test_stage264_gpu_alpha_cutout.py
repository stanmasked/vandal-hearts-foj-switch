"""Generated-only classifier fixtures. Fake PIL frames are never runtime proof."""
from pathlib import Path
import struct
import tempfile
import unittest
from PIL import Image

from tools.foj_stage263_generated_depth_sd import TRIANGLES
from tools.foj_stage261_projection_audit import projected_vertices
from tools.foj_stage264_generated_alpha_sd import masked_dds,HOLE_U,HOLE_V,install_alpha
from tools.foj_stage264_gpu_alpha_check import inspect,verify
from tools.foj_stage260_generated_gpu_sd import COLORS

def make_image(path:Path,masked:bool,*,no_discard=False,
               wrong_material=False,remove_far=False,
               background=(54,31,59)):
    im=Image.new("RGB",(1280,720),background)
    px=im.load()
    # Far cool triangle, then near warm triangle with optional fragment discard.
    for material in ("cool","warm"):
        if material=="cool" and remove_far:
            continue
        tri=projected_vertices(1280,720,TRIANGLES[material])
        (ax,ay),(bx,by),(cx,cy)=tri
        den=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
        for y in range(min(ay,by,cy),max(ay,by,cy)+1):
            for x in range(min(ax,bx,cx),max(ax,bx,cx)+1):
                b=((x-ax)*(cy-ay)-(y-ay)*(cx-ax))/den
                c=((bx-ax)*(y-ay)-(by-ay)*(x-ax))/den
                a=1-b-c
                if min(a,b,c)<0:
                    continue
                u=b+.5*c
                v=a+b
                if material=="warm" and masked and not no_discard and (
                    HOLE_U[0]<=u<=HOLE_U[1] and HOLE_V[0]<=v<=HOLE_V[1]
                ):
                    continue
                col=COLORS[0 if material=="warm" else 1]
                if wrong_material and material=="warm":
                    col=COLORS[1]
                px[x,y]=col[:3]
    im.save(path)

def pair(root:Path,scenario:str,**opts):
    folder=root/scenario
    folder.mkdir(parents=True)
    masked=scenario=="masked"
    make_image(folder/"gpu-initial.png",masked,**opts)
    make_image(folder/"gpu-later.png",masked,
               background=(112,145,110),**opts)

class AlphaUnitTests(unittest.TestCase):
    def test_alpha_dds_has_exact_solid_colored_zero_alpha_hole(self):
        original=masked_dds(False)
        aperture=masked_dds(True)
        self.assertEqual(len(original),128+64*64*4)
        self.assertEqual(aperture[:128],original[:128])
        zero_positions=[(x,y) for y in range(64) for x in range(64)
                        if aperture[128+(y*64+x)*4+3]==0]
        self.assertGreater(len(zero_positions),80)
        self.assertLess(len(zero_positions),320)
        for x,y in zero_positions:
            i=128+4*(y*64+x)
            self.assertEqual(aperture[i:i+3],original[i:i+3])
        self.assertTrue(all(original[128+4*i+3]==255
                            for i in range(64*64)))
        self.assertEqual(struct.unpack_from("<II",original,12),(64,64))

    def test_generated_reference_a_and_counterfactual_are_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            pair(root,"masked")
            pair(root,"opaque")
            proof=verify(root)
            self.assertEqual(proof["actual_neixum_guest_frames_verified"],4)
            self.assertTrue(proof["near_first_transparent_fragment_exposes_far_second_material"])

    def test_no_discard_while_alpha_zero_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            pair(root,"masked",no_discard=True)
            with self.assertRaises(ValueError):
                inspect(root/"masked"/"gpu-initial.png","masked")

    def test_incorrect_hole_in_opaque_counterfactual_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            pair(root,"masked")
            folder=root/"opaque";folder.mkdir()
            make_image(folder/"gpu-initial.png",True)
            with self.assertRaises(ValueError):
                inspect(folder/"gpu-initial.png","opaque")

    def test_missing_background_material_and_wrong_material_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for key,settings in (
                ("none",{"remove_far":True}),
                ("swap",{"wrong_material":True}),
            ):
                folder=root/key;folder.mkdir()
                make_image(folder/"fail.png",True,**settings)
                with self.subTest(key=key),self.assertRaises(ValueError):
                    inspect(folder/"fail.png","masked")

    def test_missing_and_duplicate_frame_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            pair(root,"masked");pair(root,"opaque")
            (root/"masked"/"gpu-later.png").unlink()
            with self.assertRaises(OSError):
                verify(root)
            (root/"masked"/"gpu-later.png").write_bytes(
                (root/"masked"/"gpu-initial.png").read_bytes()
            )
            with self.assertRaises(ValueError):
                verify(root)

    def test_private_path_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"user-files";root.mkdir()
            (root/"do-not-touch").write_bytes(b"private")
            with self.assertRaises(ValueError):
                install_alpha(root,Path(tmp),"masked")
            self.assertEqual((root/"do-not-touch").read_bytes(),b"private")

if __name__=="__main__":
    unittest.main()
