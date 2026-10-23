"""Stage329 screenshot auditor tests use host-painted fixtures only, never GPU evidence."""
from __future__ import annotations
import json
import os
import subprocess
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
    """Paint a host-only approximation of the native 16x16 four-quadrant draw."""
    image = Image.new("RGB", (1280, 720), background)
    pixels = image.load()

    def texel(ix: int, iy: int) -> tuple[int, int, int]:
        ix = max(0, min(15, ix))
        iy = max(0, min(15, iy))
        return COLORS[(2 if iy >= 8 else 0) + (1 if ix >= 8 else 0)][:3]

    def sample(u: float, v: float) -> tuple[int, int, int]:
        fx, fy = u * 16.0 - 0.5, v * 16.0 - 0.5
        x0, y0 = int(fx // 1), int(fy // 1)
        ax, ay = fx - x0, fy - y0
        p00, p10 = texel(x0, y0), texel(x0 + 1, y0)
        p01, p11 = texel(x0, y0 + 1), texel(x0 + 1, y0 + 1)
        return tuple(round(
            (1.0 - ay) * ((1.0 - ax) * p00[k] + ax * p10[k]) +
            ay * ((1.0 - ax) * p01[k] + ax * p11[k])
        ) for k in range(3))

    # Approximate the native projection: apex at (640,264), base at y=456.
    # Host-painted fixtures test the auditor only and are never GPU evidence.
    for y in range(264, 457):
        apex_weight = (456.0 - y) / 192.0
        if not 0.0 <= apex_weight <= 1.0:
            continue
        base_weight = 1.0 - apex_weight
        half_width = 96.0 * base_weight
        if half_width <= 0.0:
            continue
        left, right = 640.0 - half_width, 640.0 + half_width
        for x in range(max(0, int(left)), min(1279, int(right)) + 1):
            if not left <= x <= right:
                continue
            across = (x - left) / (2.0 * half_width)
            u = apex_weight * 0.5 + base_weight * (0.015625 + 0.96875 * across)
            v = apex_weight * 0.015625 + base_weight * 0.984375
            pixels[x, y] = sample(u, v)
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

    def test_early_guest_exit_diagnostic_is_bounded_and_keeps_log_private(self):
        # Pure host fixture: no NeXium and no original game assets are launched.
        fake = self.root / "fake-nexium"
        fake.write_text(
            "#!/bin/sh\n"
            "printf '%s\n' 'UNSAFE_RUNTIME_LINE_ONLY_IN_GUEST_LOG'\n"
            "printf '%s\n' 'FOJBOOT1 slot=00 step=06 event=2 frames=0000000000' "
            '> "$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu/foj-boot-12.txt"\n'
            "exit 23\n"
        )
        fake.chmod(0o700)
        nro = self.root / "generated-fixture.nro"
        nro.write_bytes(b"mock-only NRO input")
        env = os.environ.copy()
        env.update({
            "NEXIUM_BIN": str(fake),
            "FOJ_NRO": str(nro),
            "NEXIUM_DATA_ROOT": str(self.root),
            "FOJ_EVIDENCE_DIR": str(self.bridge),
        })
        result = subprocess.run(
            ["bash", "tools/foj_stage329_nexium_drive.sh"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, check=False, timeout=15,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("STAGE329_EARLY_EXIT_DIAG_V1", result.stderr)
        self.assertIn("guest_exit=23", result.stderr)
        self.assertIn("upload_marker=0", result.stderr)
        self.assertIn("boot=step=06,event=2,frames=0000000000", result.stderr)
        self.assertNotIn("UNSAFE_RUNTIME_LINE_ONLY_IN_GUEST_LOG",
                         result.stdout + result.stderr)

    def test_native_source_wires_stage328_and_upload_receipt(self):
        source = Path("gpu/deko3d_clear_main.c").read_text()
        makefile = Path("gpu/stage329_corner_patch_draw.mk").read_text()
        self.assertIn("stage329_prepare_corner_patch", source)
        self.assertIn("foj_stage328_prepare_corner_patch_stream", source)
        self.assertIn("dkQueueWaitIdle(queue);", source)
        marker_index = source.index("FOJ_NATIVE_STAGE329_CORNER_PATCH_UPLOAD_V1")
        self.assertGreater(source.rfind("dkQueueWaitIdle(queue);", 0, marker_index), -1)
        self.assertIn("0xd5565bfb7360b325", source)
        self.assertIn("504.25f/1024.f", source)
        self.assertIn("519.75f/1024.f", source)
        self.assertIn("Stage324/327 remap only tile-fragment UVs to [0,1]", source)
        self.assertIn("if(vertex->u<0.f || vertex->u>1.f", source)
        self.assertNotIn("vertex->u=local_u", source)
        self.assertIn("9.5f,0.f,0.f,1.f,1};", source)
        self.assertIn("memcpy(pixels,stage329_tile,sizeof(stage329_tile))", source)
        self.assertIn("gpu/stage328_atomic_corner_patch_stream.c", makefile)
        self.assertIn("FOJ_GPU_STAGE329_PATCH_STREAM=1", makefile)
        self.assertIn("FOJ_GPU_STAGE309_LINEAR_GUTTER=1", makefile)

if __name__ == "__main__":
    unittest.main()
