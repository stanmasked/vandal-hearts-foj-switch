"""Stage276 synthetic-only classifier and spatial alpha byte regressions.

Mock screenshots prove the *checker*, never actual NeXium GPU execution.
"""
from __future__ import annotations
import hashlib
import ctypes as c
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
from tools.foj_stage276_spatial_alpha_sd import (
    CASES,PROBES,SCHEMA,WIDTH,SPLIT_X,expected_at,
    near_atlas,target_rgb,
)
from tools.foj_stage276_spatial_alpha_check import inspect,verify
from test_stage274_actual_native_chain import compile_pipeline,AtlasInfo


def fake_evidence(root:Path):
    pristine=generated_dds((*VIOLET,128))
    for case in CASES:
        dest=root/case
        dest.mkdir()
        payload=near_atlas(case)
        digest=hashlib.sha256(payload).hexdigest()
        info={
            "schema":SCHEMA,
            "scenario":case,
            "generated_only":True,
            "original_ps3_resources":False,
            "actual_gpu_render_verified":False,
            "changed_file":"material0.dds",
            "near_original_dds_sha256":hashlib.sha256(pristine).hexdigest(),
            "near_dds_sha256":digest,
            "near_alpha_split_x":SPLIT_X,
            "near_texture_dimensions":[WIDTH,WIDTH],
            "expected_native_pass_order":[2,1,0],
            "expected_probe_rgb":{
                name:list(expected_at(case,name)) for name in PROBES},
        }
        (dest/"generated-input.json").write_text(json.dumps(info))
        for phase in ("before","after"):
            (dest/f"near-dds-{phase}.sha256").write_text(digest+"\n")
        (dest/"native-sort-pass.txt").write_bytes(
            b"FOJ_NATIVE_SORT_V1 2,1,0\n")
        (dest/"native-alpha-pass.txt").write_bytes(
            b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0\n")
        (dest/"guest.log").write_text("mock fixture; NOT NeXium\n")
        for name,back in (
            ("gpu-initial.png",(112,145,110)),
            ("gpu-later.png",(54,31,59)),
        ):
            im=Image.new("RGB",(1280,720),back)
            draw=ImageDraw.Draw(im)
            for probe,(x,y) in PROBES.items():
                draw.rectangle((x-6,y-6,x+6,y+6),
                               fill=expected_at(case,probe))
            im.save(dest/name)


class GeneratedSpatialAlphaTests(unittest.TestCase):
    def test_violet_alpha_per_texel_only(self):
        plain=generated_dds((*VIOLET,128))
        self.assertEqual(len(plain),128+64*64*4)
        for case in CASES:
            with self.subTest(case=case):
                got=near_atlas(case)
                self.assertEqual(got[:128],plain[:128])
                changed=0
                for y in range(WIDTH):
                    for x in range(WIDTH):
                        at=128+4*(y*WIDTH+x)
                        self.assertEqual(got[at:at+3],plain[at:at+3])
                        expected=(0 if ((x<SPLIT_X)==
                             (case=="alpha-left-clear")) else 128)
                        self.assertEqual(got[at+3],expected)
                        changed+=(got[at+3]!=plain[at+3])
                self.assertEqual(changed,
                    (SPLIT_X if case=="alpha-left-clear"
                     else WIDTH-SPLIT_X)*WIDTH)

    def test_real_c11_dds_decoder_preserves_every_spatial_alpha_byte(self):
        # Compile the real C11 DDS reader/decoder via the existing Stage274
        # six-module integration harness, under both GCC and Clang. Python
        # fixtures alone cannot prove the NRO's decoder preserves alpha.
        pristine=generated_dds((*VIOLET,128))
        for compiler in ("gcc","clang"):
            with self.subTest(compiler=compiler),tempfile.TemporaryDirectory() as tmp:
                native=compile_pipeline(compiler,Path(tmp)/"stage276-dds.so")
                for case in CASES:
                    with self.subTest(case=case):
                        atlas=near_atlas(case)
                        source=(c.c_uint8*len(atlas)).from_buffer_copy(atlas)
                        capacity=256*256*4
                        decoded=(c.c_uint8*capacity)()
                        metadata=AtlasInfo()
                        self.assertEqual(native["decode"](
                            source,len(atlas),decoded,capacity,
                            c.byref(metadata)),1)
                        self.assertEqual(
                            (metadata.width,metadata.height,
                             metadata.pixel_bytes),(64,64,64*64*4))
                        self.assertEqual(bytes(decoded[:64*64*4]),atlas[128:])
                        self.assertEqual(
                            bytes(decoded[64*64*4:64*64*4+16]),
                            bytes(16))
                        # A malformed size must fail before overwriting a
                        # caller buffer or metadata: no hidden fallback to a
                        # uniform-alpha texture or partial decoded data.
                        preserved=(c.c_uint8*capacity)(*([0xA5]*capacity))
                        sentinel=AtlasInfo(31,29,37)
                        self.assertEqual(native["decode"](
                            source,len(atlas)-1,preserved,capacity,
                            c.byref(sentinel)),0)
                        self.assertEqual(bytes(preserved),bytes([0xA5])*capacity)
                        self.assertEqual(
                            (sentinel.width,sentinel.height,
                             sentinel.pixel_bytes),(31,29,37))
                # Confirm both original and modified textures decode to
                # canonical RGBA8 with unchanged RGB and exact alpha mask.
                flat_source=(c.c_uint8*len(pristine)).from_buffer_copy(pristine)
                flat_out=(c.c_uint8*(256*256*4))()
                flat_meta=AtlasInfo()
                self.assertEqual(native["decode"](
                    flat_source,len(pristine),flat_out,len(flat_out),
                    c.byref(flat_meta)),1)
                self.assertEqual(bytes(flat_out[:64*64*4]),pristine[128:])

    def test_probes_are_far_from_alpha_boundary_in_actual_projection(self):
        # Derived from the production orthographic projection scale,
        # Stage267 violet triangle XY and the public three-vertex UVs.
        # Sample positions must be well inside their intended halves;
        # otherwise filtering or edge rasterization could cause false
        # negative NeXium results unrelated to spatial alpha.
        scale=.84*min(1280,720)/2.0
        screen_row=PROBES["left_overlap"][1]
        wy=(360-screen_row)/scale
        t=(wy+.50)/(.69+.50)
        self.assertTrue(0.0<t<1.0)
        xmin=-.76+t*(-.21+.76)
        xmax=.34+t*(-.21-.34)
        umin=.5*t
        umax=1.0-.5*t
        def u_at(pixel_x):
            x=(pixel_x-640)/scale
            return umin+(x-xmin)/(xmax-xmin)*(umax-umin)
        self.assertTrue(.55<u_at(PROBES["left_overlap"][0])<.65)
        self.assertTrue(.78<u_at(PROBES["right_overlap"][0])<.82)
        self.assertLess(u_at(PROBES["left_overlap"][0])+0.05,
                        SPLIT_X/WIDTH)
        self.assertGreater(u_at(PROBES["right_overlap"][0])-0.03,
                           SPLIT_X/WIDTH)

    def test_expected_source_over_pixels_are_distinct(self):
        self.assertEqual(target_rgb(128),(111,100,162))
        self.assertEqual(target_rgb(0),(127,128,123))
        self.assertNotEqual(expected_at(CASES[0],"left_overlap"),
                            expected_at(CASES[1],"left_overlap"))
        self.assertNotEqual(expected_at(CASES[0],"right_overlap"),
                            expected_at(CASES[1],"right_overlap"))

    def test_mock_oracle_is_not_real_guest_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fake_evidence(folder)
            r=verify(folder)
            self.assertEqual(r["real_guest_rgb_frames_required"],4)
            self.assertEqual(r["actual_guest_provenance"],
                "requires real GitHub Actions NeXium guest")

    def test_uniform_flat_alpha_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fake_evidence(folder)
            p=folder/"alpha-left-clear"/"gpu-initial.png"
            im=Image.open(p).convert("RGB")
            x,y=PROBES["left_overlap"]
            ImageDraw.Draw(im).rectangle((x-6,y-6,x+6,y+6),
                                         fill=target_rgb(128))
            im.save(p)
            with self.assertRaisesRegex(ValueError,"left_overlap"):
                verify(folder)

    def test_second_case_cannot_reuse_first_scene_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fake_evidence(folder)
            copy=(folder/"alpha-left-clear"/"gpu-initial.png").read_bytes()
            (folder/"alpha-right-clear"/"gpu-initial.png").write_bytes(copy)
            with self.assertRaises(ValueError):
                verify(folder)

    def test_missing_after_dds_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fake_evidence(folder)
            (folder/"alpha-left-clear"/"near-dds-after.sha256").unlink()
            with self.assertRaisesRegex(ValueError,"Missing or linked"):
                verify(folder)

    def test_forged_before_dds_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fake_evidence(folder)
            (folder/"alpha-right-clear"/"near-dds-before.sha256").write_text(
                "f"*64+"\n")
            with self.assertRaisesRegex(ValueError,"actual DDS changed"):
                verify(folder)

    def test_incorrect_native_blend_state_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fake_evidence(folder)
            (folder/"alpha-right-clear"/"native-alpha-pass.txt").write_bytes(
                b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:1 0:1:1:0\n")
            with self.assertRaisesRegex(ValueError,"native pass-state"):
                verify(folder)

    def test_rejection_witness_forbids_positive_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fake_evidence(folder)
            (folder/"alpha-left-clear"/"native-topology-reject.txt").write_text(
                "FOJ_NATIVE_TOPOLOGY_REJECT_V1 pre_gpu=1 unsafe=1\n")
            with self.assertRaisesRegex(ValueError,"contradicts refusal"):
                verify(folder)

    def test_identical_screenshot_phases_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            fake_evidence(folder)
            p=folder/"alpha-left-clear"
            (p/"gpu-later.png").write_bytes((p/"gpu-initial.png").read_bytes())
            with self.assertRaisesRegex(ValueError,"duplicate guest captures"):
                verify(folder)


if __name__=="__main__":
    unittest.main()
