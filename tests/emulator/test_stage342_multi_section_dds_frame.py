from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

from PIL import Image

from tools.foj_stage340_fixture import create
from tools.foj_stage342_generated_diagnose import diagnose
from tools.foj_stage342_frame_gate import (
    DDS_BYTES, FRAME_HEIGHT, FRAME_WIDTH, HEIGHT, MARKER, MARKER_NAME,
    SAMPLE_X_LEFT, SAMPLE_X_RIGHT, SAMPLE_Y, WIDTH, _sample_uv,
    audit_frames, decode_bgra8_dds,
)


def sample_reference(dds: bytes, wrong_one: bool = False) -> Image.Image:
    rgba = decode_bgra8_dds(dds)
    image = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), (11, 17, 23))
    pixels = image.load()
    visited = 0
    for section, xs in (("left", SAMPLE_X_LEFT), ("right", SAMPLE_X_RIGHT)):
        for y in SAMPLE_Y:
            for x in xs:
                u, v = _sample_uv(x, y, section)
                tx = min(WIDTH - 1, max(0, int(u * WIDTH)))
                ty = min(HEIGHT - 1, max(0, int(v * HEIGHT)))
                offset = (ty * WIDTH + tx) * 4
                color = tuple(rgba[offset:offset + 3])
                if wrong_one and visited == 0:
                    color = tuple(255 - channel for channel in color)
                pixels[x, y] = color
                visited += 1
    return image


def diagnostic_reference(dds: bytes) -> Image.Image:
    rgba = decode_bgra8_dds(dds)
    image = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), (11, 17, 23))
    pixels = image.load()

    def put_sample(x: int, y: int, section: str) -> None:
        u, v = _sample_uv(x, y, section)
        tx = min(WIDTH - 1, max(0, int(u * WIDTH)))
        ty = min(HEIGHT - 1, max(0, int(v * HEIGHT)))
        offset = (ty * WIDTH + tx) * 4
        pixels[x, y] = tuple(rgba[offset:offset + 3])

    # Populate the exact generated-only centerlines needed to bound both
    # quads, then all 50 oracle samples. No full screenshot is required.
    for x in range(64, 608):
        put_sample(x, FRAME_HEIGHT // 2, "left")
    for x in range(672, 1216):
        put_sample(x, FRAME_HEIGHT // 2, "right")
    for y in range(72, 648):
        put_sample(336, y, "left")
        put_sample(944, y, "right")
    for section, xs in (("left", SAMPLE_X_LEFT), ("right", SAMPLE_X_RIGHT)):
        for y in SAMPLE_Y:
            for x in xs:
                put_sample(x, y, section)
    return image


class Stage342MultiSectionFrameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sd = self.root / "sdmc"
        self.gpu = self.sd / "switch" / "foj" / "gpu"
        self.gpu.mkdir(parents=True)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.source = self.gpu / "source.dds"
        create(self.source)
        (self.gpu / "foj_actor.vert.dksh").write_bytes(b"generated vertex DKSH")
        (self.gpu / "foj_triangle.frag.dksh").write_bytes(b"generated fragment DKSH")
        (self.evidence / "guest.log").write_text("generated-only test log\n", encoding="utf-8")
        (self.evidence / "nexium-archive.sha256").write_text(
            "a" * 64 + "  nexium-linux-x86_64.tar.gz\n", encoding="ascii"
        )
        source_bytes = self.source.read_bytes()
        metadata = {
            "schema": "foj.stage340.generated_bgra8_dds_fixture.v1",
            "generated_only": True,
            "original_ps3_assets_used": False,
            "physical_switch_verified": False,
            "width": 256, "height": 256, "format": "BGRA8",
            "dds_file_bytes": DDS_BYTES,
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        }
        (self.evidence / "generated-source.json").write_text(
            json.dumps(metadata, sort_keys=True), encoding="utf-8"
        )
        (self.gpu / MARKER_NAME).write_bytes(MARKER)
        marker = self.gpu / MARKER_NAME
        old = time.time_ns() - 2_000_000_000
        os.utime(marker, ns=(old, old))
        sample_reference(source_bytes).save(self.evidence / "gpu-initial.png")
        later = sample_reference(source_bytes)
        later.putpixel((2, 2), (250, 240, 230))
        later.save(self.evidence / "gpu-later.png")

    def tearDown(self):
        self.temp.cleanup()

    def test_two_sections_sample_distinct_uv_halves(self):
        self.assertEqual(len(SAMPLE_X_LEFT), 5)
        self.assertEqual(len(SAMPLE_X_RIGHT), 5)
        self.assertEqual(len(SAMPLE_Y), 5)
        left_u, _ = _sample_uv(SAMPLE_X_LEFT[2], SAMPLE_Y[2], "left")
        right_u, _ = _sample_uv(SAMPLE_X_RIGHT[2], SAMPLE_Y[2], "right")
        self.assertLess(left_u, 0.5)
        self.assertGreater(right_u, 0.5)
        result = audit_frames(
            self.source, self.sd, self.evidence, require_generated_metadata=True
        )
        self.assertEqual(result["sections_per_frame"], 2)
        self.assertEqual(result["samples_per_frame"], 50)
        self.assertEqual(result["frame_a"]["sample_count"], 50)
        self.assertEqual(result["frame_b"]["sample_count"], 50)
        self.assertEqual(result["frame_a"]["bad_channels"], 0)
        self.assertEqual(result["frame_b"]["bad_channels"], 0)
        self.assertEqual(result["frame_a"]["max_rgb_channel_error"], 0)
        self.assertEqual(result["frame_b"]["max_rgb_channel_error"], 0)

    def test_gate_rejects_wrong_sample_in_either_section(self):
        source_bytes = self.source.read_bytes()
        sample_reference(source_bytes, wrong_one=True).save(
            self.evidence / "gpu-initial.png"
        )
        with self.assertRaisesRegex(ValueError, "differs from CPU reference"):
            audit_frames(
                self.source, self.sd, self.evidence, require_generated_metadata=True
            )

    def test_gate_rejects_stale_or_wrong_native_receipt(self):
        marker = self.gpu / MARKER_NAME
        marker.write_bytes(b"wrong marker\n")
        with self.assertRaisesRegex(ValueError, "receipt mismatch"):
            audit_frames(
                self.source, self.sd, self.evidence, require_generated_metadata=True
            )

    def test_nro_has_two_contiguous_batches_and_aliases_uploaded_source(self):
        root = Path(__file__).resolve().parents[2]
        main = (root / "gpu" / "deko3d_clear_main.c").read_text()
        self.assertIn("FOJ_GPU_STAGE342_MULTI_SECTION_DDS_DRAW", main)
        self.assertIn("FojGpuVertex stage342_sections[12]", main)
        self.assertIn("FojGpuBatch stage342_batches[2]={{0u,6u,0u},{6u,6u,1u}};", main)
        self.assertIn("texture_views[i]=stage341_source.image_view;", main)
        self.assertIn("FOJ_STAGE342_PRIVATE_DDS_MULTI_SECTION_V1", main)
        self.assertIn("foj-stage342-multi-section-sample.txt", main)
        self.assertIn("dkCmdBufDraw(cmd,DkPrimitive_Triangles", main)

    def test_stage341_single_quad_mode_remains_independent(self):
        root = Path(__file__).resolve().parents[2]
        main = (root / "gpu" / "deko3d_clear_main.c").read_text()
        self.assertIn("FOJ_GPU_STAGE341_PRIVATE_DDS_DRAW", main)
        self.assertIn("FojGpuVertex stage341_quad[6]", main)
        self.assertIn("foj-stage341-texture-sample.txt", main)

    def test_public_workflow_uses_generated_fixture_and_exports_aggregate_only(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github" / "workflows" /
                    "stage342-multi-section-dds-frame.yml").read_text()
        self.assertIn("tools.foj_stage340_fixture create", workflow)
        self.assertIn("foj-stage342-generated-only-multi-section-frame-aggregate", workflow)
        self.assertIn("path: runtime-evidence-public/", workflow)
        self.assertNotIn("FoJ_Stage340_Selected_Original_DDS", workflow)
        self.assertNotIn("path: runtime-evidence/", workflow)

    def test_private_runner_requires_external_originals_and_runtime(self):
        root = Path(__file__).resolve().parents[2]
        runner = (root / "tools" / "foj_stage342_private_run.py").read_text()
        self.assertIn("under(nexium.resolve(), REPO_ROOT)", runner)
        self.assertIn("under(shader_dir.resolve(), REPO_ROOT)", runner)
        self.assertIn("under(library_path.resolve(), REPO_ROOT)", runner)
        self.assertIn("under(icd.resolve(), REPO_ROOT)", runner)

    def test_generated_failure_diagnostic_accepts_two_section_contract(self):
        source_bytes = self.source.read_bytes()
        diagnostic_reference(source_bytes).save(self.evidence / "gpu-initial.png")
        later = diagnostic_reference(source_bytes)
        later.putpixel((2, 2), (250, 240, 230))
        later.save(self.evidence / "gpu-later.png")
        result = diagnose(self.sd, self.evidence)
        self.assertTrue(result["generated_only"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["frame_a"]["samples_checked"], 50)
        self.assertEqual(
            result["frame_a"]["generated_quad_centerline_bounds"]
                  ["horizontal_xy_pixels"],
            [[64, 607], [672, 1215]],
        )
        self.assertEqual(
            result["frame_a"]["generated_quad_centerline_bounds"]
                  ["vertical_xy_pixels"],
            [[[72, 647]], [[72, 647]]],
        )


if __name__ == "__main__":
    unittest.main()
