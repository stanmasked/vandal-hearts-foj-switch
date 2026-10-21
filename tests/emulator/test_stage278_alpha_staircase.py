"""Stage278 host-only fixture and native C11 DDS parity regressions.

Mock RGB frames validate only the independent classifier. Never claim
NeXium execution or physical Nintendo Switch GPU support from these tests.
"""
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
from tools.foj_stage278_alpha_staircase_sd import (
    CASES,PROBES,SCHEMA,BAND_SPLITS,BAND_NAMES,ALPHA_BANDS,WIDTH,
    expected_at,near_atlas,target_rgb,
)
from tools.foj_stage278_alpha_staircase_check import verify
from test_stage274_actual_native_chain import compile_pipeline,AtlasInfo


def fixture(root:Path):
    pristine=generated_dds((*VIOLET,128))
    for case in CASES:
        folder=root/case
        folder.mkdir()
        masked=near_atlas(case)
        digest=hashlib.sha256(masked).hexdigest()
        report={
            "schema":SCHEMA,"scenario":case,"generated_only":True,
            "original_ps3_resources":False,"actual_gpu_render_verified":False,
            "changed_file":"material0.dds",
            "near_original_dds_sha256":hashlib.sha256(pristine).hexdigest(),
            "near_dds_sha256":digest,
            "near_alpha_band_splits":list(BAND_SPLITS),
            "near_alpha_values":list(ALPHA_BANDS[case]),
            "near_texture_dimensions":[WIDTH,WIDTH],
            "expected_native_pass_order":[2,1,0],
            "expected_probe_rgb":{
                name:list(expected_at(case,name)) for name in PROBES},
        }
        (folder/"generated-input.json").write_text(
            json.dumps(report),encoding="utf-8")
        for phase in ("before","after"):
            (folder/f"near-dds-{phase}.sha256").write_text(
                digest+"\n",encoding="ascii")
        (folder/"native-sort-pass.txt").write_bytes(
            b"FOJ_NATIVE_SORT_V1 2,1,0\n")
        (folder/"native-alpha-pass.txt").write_bytes(
            b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0\n")
        (folder/"guest.log").write_text(
            "synthetic classifier only; NOT REAL NeXium\n",encoding="utf-8")
        for name,background in (
                ("gpu-initial.png",(112,145,110)),
                ("gpu-later.png",(54,31,59))):
            frame=Image.new("RGB",(1280,720),background)
            painter=ImageDraw.Draw(frame)
            for label,(x,y) in PROBES.items():
                painter.rectangle((x-6,y-6,x+6,y+6),
                                  fill=expected_at(case,label))
            frame.save(folder/name)


def uv_at(x:int,y:int)->float:
    # Stage275 orthographic projection, same public actor and camera.
    scale=.84*min(1280,720)/2.
    level=(((360-y)/scale)+.50)/(.69+.50)
    lo=-.76+level*.55
    hi=.34-level*.55
    start=.5*level
    end=1.-.5*level
    return start+(((x-640)/scale)-lo)/(hi-lo)*(end-start)


class Stage278FourBandAlphaTests(unittest.TestCase):
    def test_exact_four_bands_and_unchanged_rgb_header(self):
        pristine=generated_dds((*VIOLET,128))
        self.assertEqual(len(pristine),16512)
        for case in CASES:
            with self.subTest(case=case):
                atlas=near_atlas(case)
                self.assertEqual(atlas[:128],pristine[:128])
                for y in range(64):
                    for x in range(64):
                        offset=128+4*(64*y+x)
                        self.assertEqual(atlas[offset:offset+3],
                                         pristine[offset:offset+3])
                        band=sum(x>=bound for bound in BAND_SPLITS)
                        self.assertEqual(
                            atlas[offset+3],ALPHA_BANDS[case][band])
                self.assertEqual(len(atlas),len(pristine))

    def test_four_distinct_cpu_blend_colors(self):
        self.assertEqual(target_rgb(0),(127,128,123))
        self.assertEqual(target_rgb(64),(119,114,143))
        self.assertEqual(target_rgb(128),(111,100,162))
        self.assertEqual(target_rgb(255),(96,72,201))
        for band in BAND_NAMES:
            self.assertNotEqual(
                expected_at(CASES[0],band),expected_at(CASES[1],band))

    def test_all_81_pixels_per_band_are_inside_uv_interval(self):
        ranges=((0.,40/64.),(40/64.,44/64.),
                (44/64.,49/64.),(49/64.,1.))
        for name,(lo,hi) in zip(BAND_NAMES,ranges):
            px,py=PROBES[name]
            footprint=[uv_at(x,y) for y in range(py-4,py+5)
                                 for x in range(px-4,px+5)]
            self.assertEqual(len(footprint),81)
            self.assertGreater(min(footprint),lo+.008)
            self.assertLess(max(footprint),hi-.008)

    def test_classifier_fixture_is_not_real_neixum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            report=verify(root)
            self.assertEqual(report["real_guest_rgb_frames_required"],4)
            self.assertEqual(report["actual_guest_provenance"],
                             "requires real GitHub Actions NeXium guest")

    def test_constant_alpha_frame_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            path=root/CASES[0]/"gpu-initial.png"
            image=Image.open(path).convert("RGB")
            x,y=PROBES["band_0"]
            ImageDraw.Draw(image).rectangle((x-6,y-6,x+6,y+6),
                                             fill=target_rgb(128))
            image.save(path)
            with self.assertRaisesRegex(ValueError,"band_0"):
                verify(root)

    def test_reused_case_frame_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/CASES[1]/"gpu-initial.png").write_bytes(
                (root/CASES[0]/"gpu-initial.png").read_bytes())
            with self.assertRaises(ValueError):
                verify(root)

    def test_missing_dds_snapshot_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/CASES[0]/"near-dds-after.sha256").unlink()
            with self.assertRaisesRegex(ValueError,"Missing or linked"):
                verify(root)

    def test_forged_pre_guest_dds_hash_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/CASES[1]/"near-dds-before.sha256").write_text(
                "0"*64+"\n",encoding="ascii")
            with self.assertRaisesRegex(ValueError,"actual DDS changed"):
                verify(root)

    def test_wrong_native_pass_receipt_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/CASES[1]/"native-alpha-pass.txt").write_bytes(
                b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:1 0:1:1:0\n")
            with self.assertRaisesRegex(ValueError,"native pass-state"):
                verify(root)

    def test_negative_refusal_contradicts_positive_guest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            (root/CASES[0]/"native-topology-reject.txt").write_bytes(
                b"FOJ_NATIVE_TOPOLOGY_REJECT_V1 pre_gpu=1 unsafe=1\n")
            with self.assertRaisesRegex(ValueError,"contradicts refusal"):
                verify(root)

    def test_duplicate_phase_images_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fixture(root)
            path=root/CASES[0]
            (path/"gpu-later.png").write_bytes(
                (path/"gpu-initial.png").read_bytes())
            with self.assertRaisesRegex(ValueError,"duplicate guest captures"):
                verify(root)

    def test_production_c11_dds_decoder_matches_both_stripe_masks(self):
        for compiler in ("gcc","clang"):
            with self.subTest(compiler=compiler),tempfile.TemporaryDirectory() as tmp:
                native=compile_pipeline(compiler,Path(tmp)/"stage278-dds.so")
                cap=256*256*4
                for case in CASES:
                    with self.subTest(case=case):
                        expected=near_atlas(case)
                        src=(c.c_uint8*len(expected)).from_buffer_copy(expected)
                        out=(c.c_uint8*cap)()
                        metadata=AtlasInfo()
                        self.assertEqual(native["decode"](
                            src,len(expected),out,cap,c.byref(metadata)),1)
                        self.assertEqual(
                            (metadata.width,metadata.height,
                             metadata.pixel_bytes),(64,64,16384))
                        self.assertEqual(bytes(out[:16384]),expected[128:])
                        self.assertEqual(bytes(out[16384:16384+16]),bytes(16))
                        guard=(c.c_uint8*cap)(*([0xA5]*cap))
                        sentinel=AtlasInfo(31,29,37)
                        self.assertEqual(native["decode"](
                            src,len(expected)-1,guard,cap,c.byref(sentinel)),0)
                        self.assertEqual(bytes(guard),bytes([0xA5])*cap)
                        self.assertEqual(
                            (sentinel.width,sentinel.height,
                             sentinel.pixel_bytes),(31,29,37))


if __name__=="__main__":
    unittest.main()
