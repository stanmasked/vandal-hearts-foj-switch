"""Stage280 host-only alpha edge classifier and production DDS decoder parity."""
from __future__ import annotations
import ctypes as c
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
from tools.foj_stage280_shifted_boundary_sd import (
    CASES,SPLITS,FRAME_CROSSINGS,PROFILE_Y,SCHEMA,WIDTH,
    positions,profile_x,expected_at,near_atlas,target_rgb,
)
from tools.foj_stage280_shifted_boundary_check import verify,inspect
from test_stage274_actual_native_chain import compile_pipeline,AtlasInfo


def mock_files(root:Path):
    pristine=generated_dds((*VIOLET,128))
    for case in CASES:
        folder=root/case
        folder.mkdir()
        data=near_atlas(case)
        digest=hashlib.sha256(data).hexdigest()
        metadata={
            "schema":SCHEMA,"scenario":case,"generated_only":True,
            "original_ps3_resources":False,"actual_gpu_render_verified":False,
            "changed_file":"material0.dds",
            "near_original_dds_sha256":hashlib.sha256(pristine).hexdigest(),
            "near_dds_sha256":digest,
            "near_alpha_split_x":SPLITS[case],
            "expected_half_transition_x":FRAME_CROSSINGS[case],
            "near_texture_dimensions":[WIDTH,WIDTH],
            "profile_x_positions":list(profile_x(case)),
            "profile_y":PROFILE_Y,
            "profile_goal":"verify UV-driven shift, never infer sampler mode",
            "expected_native_pass_order":[2,1,0],
            "expected_probe_rgb":{
                name:list(expected_at(case,name)) for name in positions(case)},
        }
        (folder/"generated-input.json").write_text(json.dumps(metadata))
        for phase in ("before","after"):
            (folder/f"near-dds-{phase}.sha256").write_text(digest+"\n")
        (folder/"native-sort-pass.txt").write_bytes(
            b"FOJ_NATIVE_SORT_V1 2,1,0\n")
        (folder/"native-alpha-pass.txt").write_bytes(
            b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0\n")
        (folder/"guest.log").write_text("synthetic-only; not NeXium execution\n")
        for name,background in (
                ("gpu-initial.png",(112,145,110)),
                ("gpu-later.png",(54,31,59))):
            im=Image.new("RGB",(1280,720),background)
            draw=ImageDraw.Draw(im)
            for label,(x,y) in positions(case).items():
                draw.rectangle((x-5,y-5,x+5,y+5),fill=expected_at(case,label))
            for x in profile_x(case):
                alpha=0 if x<FRAME_CROSSINGS[case] else 255
                draw.point((x,PROFILE_Y),fill=target_rgb(alpha))
            im.save(folder/name)


class Stage280BoundaryTests(unittest.TestCase):
    def test_generated_masks_are_exact_binary_alpha_and_unmodified_rgb(self):
        original=generated_dds((*VIOLET,128))
        for case in CASES:
            with self.subTest(case=case):
                dds=near_atlas(case)
                self.assertEqual(len(dds),16512)
                self.assertEqual(dds[:128],original[:128])
                for y in range(WIDTH):
                    for x in range(WIDTH):
                        pos=128+4*(y*WIDTH+x)
                        self.assertEqual(dds[pos:pos+3],original[pos:pos+3])
                        alpha=0 if x<SPLITS[case] else 255
                        self.assertEqual(dds[pos+3],alpha)

    def test_mock_nearest_boundary_is_accepted_without_sampler_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            record=verify(root)
            for case in CASES:
                current=record["cases"][case]["initial"]
                self.assertEqual(current["half_transition_x"],
                                 FRAME_CROSSINGS[case])
                self.assertEqual(current["intermediate_sample_count"],0)
                self.assertEqual(current["sampler_filter_mode"],"NOT_INFERRED")

    def test_mock_intermediate_gradient_accepted_without_sampler_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            from tools.foj_stage280_shifted_boundary_check import (
                REFERENCE_CLEAR,DELTA,
            )
            for case in CASES:
                folder=root/case
                for name in ("gpu-initial.png","gpu-later.png"):
                    path=folder/name
                    im=Image.open(path).convert("RGB")
                    pixels=im.load()
                    center=FRAME_CROSSINGS[case]
                    for x in range(center-3,center+4):
                        alpha=max(0.,min(1.,(x-(center-4))/8.))
                        pixels[x,PROFILE_Y]=tuple(
                            round(REFERENCE_CLEAR[i]+alpha*DELTA[i])
                            for i in range(3))
                    im.save(path)
            summary=verify(root)
            for case in CASES:
                self.assertGreater(
                    summary["cases"][case]["initial"]
                           ["intermediate_sample_count"],0)

    def test_wrong_transition_location_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            folder=root/CASES[0]
            for name in ("gpu-initial.png","gpu-later.png"):
                path=folder/name
                im=Image.open(path).convert("RGB")
                for x in profile_x(CASES[0]):
                    # shift transition far away but preserve control colors
                    if FRAME_CROSSINGS[CASES[0]]-10<=x<=FRAME_CROSSINGS[CASES[0]]+9:
                        im.putpixel((x,PROFILE_Y),target_rgb(0))
                im.save(path)
            with self.assertRaises(ValueError):
                verify(root)

    def test_off_curve_color_rejected_even_with_in_range_opacity(self):
        # A black pixel projects to an in-range scalar alpha along the
        # expected RGB vector, but has a large residual perpendicular to
        # the physically valid straight-alpha color path. This exercises
        # the independent three-channel curve check.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            path=root/CASES[0]/"gpu-initial.png"
            im=Image.open(path).convert("RGB")
            im.putpixel((FRAME_CROSSINGS[CASES[0]]+1,PROFILE_Y),(0,0,0))
            im.save(path)
            with self.assertRaisesRegex(ValueError,"not on source-over curve"):
                verify(root)

    def test_opacity_outside_source_over_envelope_rejected(self):
        # White projects slightly below -0.07 into the CPU's normalized
        # 0..1 alpha axis and must fail the envelope check, independent
        # of the off-curve color residual guard.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            path=root/CASES[0]/"gpu-initial.png"
            im=Image.open(path).convert("RGB")
            im.putpixel((661,PROFILE_Y),(255,255,255))
            im.save(path)
            with self.assertRaisesRegex(ValueError,"out-of-envelope"):
                verify(root)

    def test_nonmonotonic_profile_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            path=root/CASES[0]/"gpu-initial.png"
            im=Image.open(path).convert("RGB")
            im.putpixel((653,PROFILE_Y),target_rgb(255))
            im.save(path)
            with self.assertRaisesRegex(ValueError,"nonmonotone"):
                verify(root)

    def test_two_projected_alpha_edges_have_distinct_locations(self):
        # Both cases share identical XY and RGB. Their expected source DDS
        # boundaries differ by 12 texels, which maps to about 62.4 screen
        # pixels in the actual Stage275 camera. Test measured mock ranges
        # and independent source UV mapping; mock alone is not GPU proof.
        self.assertEqual((SPLITS[CASES[0]],SPLITS[CASES[1]]),(40,52))
        self.assertEqual(
            FRAME_CROSSINGS[CASES[1]]-FRAME_CROSSINGS[CASES[0]],62)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            results=verify(root)["cases"]
            self.assertEqual([
                results[c]["initial"]["half_transition_x"] for c in CASES],
                [FRAME_CROSSINGS[c] for c in CASES])

    def test_missing_post_guest_dds_hash_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            (root/CASES[1]/"near-dds-after.sha256").unlink()
            with self.assertRaisesRegex(ValueError,"Missing or linked"):
                verify(root)

    def test_wrong_native_blend_state_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            (root/CASES[0]/"native-alpha-pass.txt").write_text(
                "FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:1 0:1:1:0\n")
            with self.assertRaisesRegex(ValueError,"native GPU descriptor"):
                verify(root)

    def test_duplicate_frame_cannot_be_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            mock_files(root)
            folder=root/CASES[0]
            (folder/"gpu-later.png").write_bytes(
                (folder/"gpu-initial.png").read_bytes())
            with self.assertRaisesRegex(ValueError,"duplicate framebuffer"):
                verify(root)

    def test_native_decoder_preserves_binary_alpha_and_rejects_truncation(self):
        cap=256*256*4
        for compiler in ("gcc","clang"):
            with self.subTest(compiler=compiler),tempfile.TemporaryDirectory() as tmp:
                native=compile_pipeline(compiler,Path(tmp)/"stage280-dds.so")
                for case in CASES:
                    with self.subTest(case=case):
                        dds=near_atlas(case)
                        source=(c.c_uint8*len(dds)).from_buffer_copy(dds)
                        pixels=(c.c_uint8*cap)()
                        meta=AtlasInfo()
                        self.assertEqual(native["decode"](
                            source,len(dds),pixels,cap,c.byref(meta)),1)
                        self.assertEqual(
                            (meta.width,meta.height,meta.pixel_bytes),
                            (64,64,16384))
                        self.assertEqual(bytes(pixels[:16384]),dds[128:])
                        guard=(c.c_uint8*cap)(*([0xA5]*cap))
                        original=AtlasInfo(31,29,37)
                        self.assertEqual(native["decode"](
                            source,len(dds)-1,guard,cap,c.byref(original)),0)
                        self.assertEqual(bytes(guard),bytes([0xA5])*cap)
                        self.assertEqual(
                            (original.width,original.height,
                             original.pixel_bytes),(31,29,37))


if __name__=="__main__":
    unittest.main()
