"""Stage329 screenshot auditor tests use host-painted fixtures only, never GPU evidence."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw

from tools.foj_stage329_corner_patch_guest import (
    MARKER, MARKER_BYTES, RECEIPT, PUBLIC_FILES, _origin, _frame, audit, prepare, publish,
)

COLORS = (
    (255, 0, 0), (0, 255, 0),
    (0, 0, 255), (255, 255, 255),
)

def fake_frame(path: Path, background: tuple[int, int, int]) -> None:
    """Paint a host-only triangle with the expected four-color bilinear pattern."""
    image = Image.new("RGB", (1280, 720), background)
    pixels = image.load()
    for y in range(158, 462):
        t = (y - 158) / 303.0
        half_width = 101.0 * t
        left = max(0, int(640 - half_width))
        right = min(1279, int(640 + half_width))
        for x in range(left, right + 1):
            tu = max(0.0, min(1.0, 0.5 + (x - 640) * 0.000633663366))
            tv = max(0.0, min(1.0, 0.5 + (y - 360) * 0.000633663366))
            tx = max(0.0, min(1.0, tu * 16.0 - 7.5))
            ty = max(0.0, min(1.0, tv * 16.0 - 7.5))
            weights = (
                (1.0 - tx) * (1.0 - ty), tx * (1.0 - ty),
                (1.0 - tx) * ty, tx * ty,
            )
            rgb = tuple(round(sum(weights[i] * COLORS[i][c] for i in range(4)))
                        for c in range(3))
            pixels[x, y] = rgb
    image.save(path)

def mock_evidence(root: Path) -> tuple[Path, Path]:
    sd = root / "sdmc"
    gpu = sd / "switch" / "foj" / "gpu"
    gpu.mkdir(parents=True)
    (gpu / "foj_actor.vert.dksh").write_bytes(b"generated vertex shader fixture")
    (gpu / "foj_triangle.frag.dksh").write_bytes(b"generated fragment shader fixture")
    bridge = root / "source" / "bridge"
    bridge.mkdir(parents=True)
    (bridge / "generated-input.json").write_text(
        json.dumps(_origin(gpu), sort_keys=True, indent=2) + "\n"
    )
    (bridge / MARKER).write_bytes(MARKER_BYTES)
    (bridge / "guest.log").write_text("host-only mock; not a NeXium log\n")
    # Match the two actual foj_smoke_color_for_frame clear colors.
    fake_frame(bridge / "gpu-initial.png", (23, 31, 59))
    fake_frame(bridge / "gpu-later.png", (112, 145, 110))
    (root / "source" / "nexium-archive.sha256").write_text(
        "a" * 64 + "  /tmp/nexium.tar.gz\n"
    )
    (bridge / RECEIPT).write_text(json.dumps(audit(bridge), sort_keys=True, indent=2) + "\n")
    return bridge, root / "source"

class Stage329GuestAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bridge, self.source = mock_evidence(self.root)

    def test_host_fixture_exercises_midpoint_and_both_gradients(self):
        report = audit(self.bridge)
        self.assertTrue(report["gpu_tile_midpoint_verified"])
        self.assertTrue(report["horizontal_and_vertical_linear_interpolation_verified"])
        self.assertTrue(report["four_quadrant_contributions_verified"])
        self.assertFalse(report["physical_switch_verified"])
        for frame in report["frames"].values():
            self.assertEqual(frame["center_x"], 640)
            self.assertEqual(frame["center_y"], 360)
            self.assertGreaterEqual(frame["horizontal_green_delta"], 28)
            self.assertGreaterEqual(frame["vertical_blue_delta"], 28)

    def test_flat_midpoint_is_not_accepted_as_gpu_filtering(self):
        path = self.bridge / "gpu-initial.png"
        with Image.open(path) as source:
            image = source.convert("RGB")
        ImageDraw.Draw(image).rectangle((619, 339, 661, 381), fill=(128, 128, 128))
        image.save(path)
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_missing_northwest_red_component_is_rejected(self):
        path = self.bridge / "gpu-initial.png"
        with Image.open(path) as source:
            image = source.convert("RGB")
        # Destroy the northwest sample and its immediate neighborhood.
        ImageDraw.Draw(image).rectangle((618, 338, 622, 342), fill=(0, 0, 0))
        image.save(path)
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_wrong_upload_receipt_is_rejected(self):
        (self.bridge / MARKER).write_bytes(b"FOJ_NATIVE_STAGE329_FAKE\n")
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_claim_of_private_or_original_assets_is_rejected(self):
        path = self.bridge / "generated-input.json"
        value = json.loads(path.read_text())
        value["original_ps3_assets_used"] = True
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_duplicate_frames_are_rejected(self):
        (self.bridge / "gpu-later.png").write_bytes(
            (self.bridge / "gpu-initial.png").read_bytes()
        )
        with self.assertRaises(ValueError):
            audit(self.bridge)

    def test_publish_is_allowlisted_and_excludes_guest_log(self):
        output = self.root / "public"
        report = publish(self.source, output)
        self.assertEqual(report["public_files"], len(PUBLIC_FILES))
        self.assertFalse((output / "bridge" / "guest.log").exists())
        self.assertEqual(set(PUBLIC_FILES), {
            "nexium-archive.sha256",
            "bridge/generated-input.json",
            "bridge/" + MARKER,
            "bridge/gpu-initial.png",
            "bridge/gpu-later.png",
            "bridge/" + RECEIPT,
        })

    def test_extra_file_is_rejected_from_public_export(self):
        (self.source / "original-ps3.bin").write_bytes(b"private")
        with self.assertRaises(ValueError):
            publish(self.source, self.root / "bad-public")

    def test_prepare_rejects_extra_sd_assets(self):
        (self.root / "sdmc" / "switch" / "foj" / "gpu" / "material0.dds").write_bytes(b"not allowed")
        with self.assertRaises(ValueError):
            prepare(self.root / "sdmc", self.root / "new-evidence")

    def test_native_source_wires_stage328_and_upload_receipt(self):
        source = Path("gpu/deko3d_clear_main.c").read_text()
        makefile = Path("gpu/stage329_corner_patch_draw.mk").read_text()
        self.assertIn("stage329_prepare_corner_patch", source)
        self.assertIn("foj_stage328_prepare_corner_patch_stream", source)
        self.assertIn("dkQueueWaitIdle(queue);", source)
        marker_index = source.index("FOJ_NATIVE_STAGE329_CORNER_PATCH_UPLOAD_V1")
        self.assertGreater(source.rfind("dkQueueWaitIdle(queue);", 0, marker_index), -1)
        self.assertIn("0xd5565bfb7360b325", source)
        self.assertIn("1.2f,0.f,0.f,1.f,1};", source)
        self.assertIn("memcpy(pixels,stage329_tile,sizeof(stage329_tile))", source)
        self.assertIn("gpu/stage328_atomic_corner_patch_stream.c", makefile)
        self.assertIn("FOJ_GPU_STAGE329_PATCH_STREAM=1", makefile)
        self.assertIn("FOJ_GPU_STAGE309_LINEAR_GUTTER=1", makefile)

if __name__ == "__main__":
    unittest.main()
