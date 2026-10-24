from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tools.foj_stage340_fixture import fixture_bytes, summary
from tools.foj_stage341_frame_gate import (
    FRAMES, READY_MARKER, SAMPLE_POINTS, _bilinear_rgb, _quad_uv,
    audit, publish_public,
)


class Stage341FrameGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.dds"
        self.blob = fixture_bytes()
        self.source.write_bytes(self.blob)
        self.source_hash = hashlib.sha256(self.blob).hexdigest()
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self._write_evidence(generated=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_frame(self, path: Path, border: tuple[int, int, int]) -> None:
        # Only sample points and the clear-color border are consumed by the gate.
        image = Image.new("RGB", (1280, 720), (32, 32, 32))
        image.putpixel((20, 20), border)
        rgba = Image.open(self.source).convert("RGBA").tobytes()
        for _, x, y in SAMPLE_POINTS:
            u, v = _quad_uv(x, y)
            rgb = _bilinear_rgb(rgba, u, v)
            image.putpixel((x, y), tuple(rgb))
        image.save(path, format="PNG")

    def _write_evidence(self, generated: bool, same_border: bool = False) -> None:
        for name in FRAMES:
            (self.evidence / name).unlink(missing_ok=True)
        (self.evidence / "source-before.sha256").write_text(
            self.source_hash + "\n", encoding="ascii"
        )
        (self.evidence / "source-after.sha256").write_text(
            self.source_hash + "\n", encoding="ascii"
        )
        (self.evidence / "ready-marker.txt").write_bytes(READY_MARKER)
        (self.evidence / "guest.log").write_text("non-fatal headless audio warning\n",
                                                   encoding="utf-8")
        (self.evidence / "nexium-archive.sha256").write_text("a" * 64 + "\n",
                                                              encoding="ascii")
        if generated:
            (self.evidence / "generated-input.json").write_text(
                json.dumps(summary(self.blob), sort_keys=True) + "\n",
                encoding="utf-8"
            )
        else:
            (self.evidence / "generated-input.json").unlink(missing_ok=True)
        self._write_frame(self.evidence / FRAMES[0], (54, 31, 59))
        self._write_frame(self.evidence / FRAMES[1],
                          (54, 31, 59) if same_border else (112, 145, 110))

    def test_generated_only_audit_passes_and_checks_five_points(self) -> None:
        report = audit(self.source, self.evidence, generated_only=True)
        self.assertEqual(report["result"], "PASS")
        self.assertTrue(report["native_upload_marker_verified"])
        self.assertEqual(report["real_neixium_frame_count"], 2)
        self.assertEqual(len(report["samples"]["initial"]), 5)
        self.assertTrue(report["generated_only"])
        self.assertIn("Stage340 independently checked all RGBA channels",
                      report["alpha_policy"])

    def test_rejects_rgb_sample_mismatch(self) -> None:
        path = self.evidence / FRAMES[0]
        with Image.open(path) as opened:
            image = opened.convert("RGB")
        _, x, y = SAMPLE_POINTS[0]
        image.putpixel((x, y), (0, 0, 0))
        image.save(path, format="PNG")
        with self.assertRaisesRegex(ValueError, "exceeded RGB tolerance"):
            audit(self.source, self.evidence, generated_only=True)

    def test_rejects_duplicate_capture_phase(self) -> None:
        self._write_evidence(generated=True, same_border=True)
        with self.assertRaisesRegex(ValueError, "stale/duplicate"):
            audit(self.source, self.evidence, generated_only=True)

    def test_rejects_changed_source_hash(self) -> None:
        (self.evidence / "source-after.sha256").write_text("b" * 64 + "\n",
                                                            encoding="ascii")
        with self.assertRaisesRegex(ValueError, "source changed"):
            audit(self.source, self.evidence, generated_only=True)

    def test_rejects_forged_native_ready_marker(self) -> None:
        (self.evidence / "ready-marker.txt").write_text(
            "FOJ_STAGE341_PRIVATE_DDS_FRAME_READY_V1\n", encoding="ascii"
        )
        with self.assertRaisesRegex(ValueError, "marker mismatch"):
            audit(self.source, self.evidence, generated_only=True)

    def test_rejects_malformed_source_dds(self) -> None:
        self.source.write_bytes(b"DDS " + b"\\x00" * 100)
        with self.assertRaisesRegex(ValueError, "bounded classic"):
            audit(self.source, self.evidence, generated_only=True)

    def test_rejects_symlink_evidence_file(self) -> None:
        (self.evidence / "guest.log").unlink()
        (self.evidence / "guest.log").symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            audit(self.source, self.evidence, generated_only=True)

    def test_rejects_missing_frame(self) -> None:
        (self.evidence / FRAMES[1]).unlink()
        with self.assertRaisesRegex(ValueError, "strict allowlist"):
            audit(self.source, self.evidence, generated_only=True)

    def test_rejects_extra_evidence_file(self) -> None:
        (self.evidence / "source.png").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "strict allowlist"):
            audit(self.source, self.evidence, generated_only=True)

    def test_public_export_contains_only_allowlisted_aggregate(self) -> None:
        report_path = self.root / "aggregate.json"
        report_path.write_text(json.dumps(
            audit(self.source, self.evidence, generated_only=True),
            sort_keys=True
        ) + "\n", encoding="utf-8")
        output = self.root / "public"
        result = publish_public(report_path, self.evidence, output)
        self.assertTrue(result["generated_only"])
        self.assertEqual(
            {p.name for p in output.iterdir()},
            {"stage341-frame-audit.json", "nexium-archive.sha256"}
        )
        self.assertFalse((output / FRAMES[0]).exists())
        self.assertFalse((output / "guest.log").exists())

    def test_public_export_rejects_source_hash_mismatch(self) -> None:
        report_path = self.root / "mismatched-aggregate.json"
        report = audit(self.source, self.evidence, generated_only=True)
        report["source_sha256"] = "b" * 64
        report_path.write_text(json.dumps(report, sort_keys=True) + "\\n",
                               encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source/provenance hash mismatch"):
            publish_public(report_path, self.evidence, self.root / "public-mismatch")

    def test_public_export_refuses_private_source_report(self) -> None:
        self._write_evidence(generated=False)
        report_path = self.root / "private-aggregate.json"
        report_path.write_text(json.dumps(
            audit(self.source, self.evidence, generated_only=False),
            sort_keys=True
        ) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "non-generated source"):
            publish_public(report_path, self.evidence, self.root / "public-refused")


if __name__ == "__main__":
    unittest.main()
