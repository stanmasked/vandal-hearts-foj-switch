"""Metadata-only synthetic tests: no commercial PS3 resources."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.foj_texture_probe import inventory
from tools.foj_texture_relations import build_relations


def make_dds() -> bytes:
    h = bytearray(128)
    h[:4] = b"DDS "
    for pos, val in [(4, 124), (8, 0x81007), (12, 8), (16, 8),
                     (20, 32), (28, 1), (76, 32), (80, 4),
                     (84, 0x31545844), (108, 0x1000)]:
        struct.pack_into("<I", h, pos, val)
    return bytes(h) + bytes(32)


def make_manifest(*records):
    return {
        "schema": "foj-texture-candidates-v1",
        "candidates": [
            {"relative_path": path, "offset": offset,
             "expected_payload_bytes": size,
             "format_candidate": fmt}
            for path, offset, size, fmt in records
        ],
    }


class TextureRelationTests(unittest.TestCase):
    def test_separated_adjacent_and_overlap_without_game_files(self):
        report = build_relations(make_manifest(
            ("z.bin", 256, 32, "BC1/DXT1"),
            ("z.bin", 416, 32, "BC3/DXT5"),
            ("z.bin", 550, 32, "BC1/DXT1"),
            ("a.dds", 0, 32, "BC1/DXT1"),
        ))
        self.assertEqual(report["pointer_scan"], "disabled")
        self.assertEqual(report["summary"]["containers_with_dds_candidates"], 2)
        self.assertEqual(report["summary"]["dds_candidates"], 4)
        self.assertEqual(report["summary"]["possible_pointer_matches"], 0)
        self.assertEqual([c["relative_path"] for c in report["containers"]],
                         ["a.dds", "z.bin"])
        values = report["containers"][1]["candidates"]
        self.assertEqual(values[0]["candidate_span_end"], 416)
        self.assertEqual(values[0]["layout_hint"], "adjacent")
        self.assertEqual(values[0]["gap_to_next_candidate_bytes"], 0)
        self.assertEqual(values[1]["layout_hint"], "overlap")
        self.assertEqual(values[1]["gap_to_next_candidate_bytes"], -26)
        self.assertEqual(values[2]["layout_hint"], "last-candidate")

    def test_unknown_size_keeps_relation_unclassified(self):
        result = build_relations(make_manifest(
            ("x", 144, None, "FourCC/12345678"),
            ("x", 560, 32, "BC1/DXT1")))
        first = result["containers"][0]["candidates"][0]
        self.assertEqual(first["layout_hint"], "size-unclassified")
        self.assertIsNone(first["candidate_span_end"])
        self.assertIsNone(first["gap_to_next_candidate_bytes"])
        self.assertEqual(first["next_candidate_offset"], 560)

    def test_optional_prefix_pointer_hints_are_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            buf = bytearray(b"\xff" * 1300)
            block = make_dds()
            buf[256:256 + len(block)] = block
            buf[1024:1024 + len(block)] = block
            struct.pack_into("<I", buf, 4, 256)  # plausible LE pointer
            struct.pack_into(">I", buf, 8, 1024)  # plausible BE pointer
            struct.pack_into("<I", buf, 384, 256)  # *inside DDS payload*: skip
            (root / "pack.bin").write_bytes(buf)
            # Source probe recovers both candidates and their offsets.
            manifest = inventory(root)
            self.assertEqual(len(manifest["candidates"]), 2)
            result = build_relations(manifest, root=root)
            self.assertEqual(result["pointer_scan"],
                             "first-file-prefix-aligned-uint32-le-be")
            self.assertEqual(result["summary"]["possible_pointer_matches"], 2)
            a, b = result["containers"][0]["candidates"]
            self.assertEqual(a["offset"], 256)
            self.assertEqual(a["layout_hint"], "separated")
            self.assertEqual(a["gap_to_next_candidate_bytes"], 608)
            self.assertEqual(a["possible_32bit_offset_references"], [{
                "word_offset": 4, "byte_order": "little",
                "interpretation": "possible-file-relative-offset"}])
            self.assertEqual(b["possible_32bit_offset_references"], [{
                "word_offset": 8, "byte_order": "big",
                "interpretation": "possible-file-relative-offset"}])
            capped = build_relations(manifest, root=root, prefix_bytes=8)
            self.assertEqual(capped["summary"]["possible_pointer_matches"], 1)
            self.assertEqual(capped["containers"][0]["candidates"][1][
                "possible_32bit_offset_references"], [])
            # No raw pixel bytes nor absolute root location appear in report.
            payload = json.dumps(result)
            self.assertNotIn(str(root), payload)
            self.assertNotIn("\\ufffd", payload)

    def test_limits_and_repeated_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            buf = bytearray(b"\xff" * 512)
            buf[256:416] = make_dds()
            for p in (0, 4, 8):
                struct.pack_into("<I", buf, p, 256)
            (root / "pack.bin").write_bytes(buf)
            report = build_relations(inventory(root), root=root,
                                     max_pointers_per_candidate=2)
            refs = report["containers"][0]["candidates"][0][
                "possible_32bit_offset_references"]
            self.assertEqual(len(refs), 2)
            self.assertEqual([ref["word_offset"] for ref in refs], [0, 4])
            with self.assertRaises(ValueError):
                build_relations(inventory(root), root=root, prefix_bytes=3)
            with self.assertRaises(ValueError):
                build_relations(inventory(root), root=root,
                                max_pointers_per_candidate=0)

    def test_reject_unsafe_or_unexpected_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("/absolute.bin", "../escaping.bin", "a/../../bad",
                         "bad\\name", "./dot.bin", "a//b"):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        build_relations(make_manifest(
                            (name, 256, 32, "BC1")), root=root)
            with self.assertRaises(ValueError):
                build_relations({"schema": "unknown", "candidates": []})
            with self.assertRaises(ValueError):
                build_relations(make_manifest(("a", -1, 32, "BC1")))
            with self.assertRaises(ValueError):
                build_relations(make_manifest(("a", 10, -4, "BC1")))
            (root / "real.bin").write_bytes(make_dds())
            (root / "symlink.bin").symlink_to(root / "real.bin")
            with self.assertRaises(ValueError):
                build_relations(make_manifest(
                    ("symlink.bin", 256, 32, "BC1")), root=root)

    def test_cli_layout_only_and_pointer_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            asset = root / "synthetic.bin"
            asset.write_bytes(b"\0" * 256 + make_dds())
            report = inventory(root)
            metadata_input = root / "local-input.json"
            metadata_input.write_text(json.dumps(report), encoding="utf-8")
            output = root / "local-output.json"
            for with_root in (False, True):
                args = [sys.executable, "-m", "tools.foj_texture_relations",
                        str(metadata_input), "--output", str(output)]
                if with_root:
                    args += ["--root", str(root)]
                cp = subprocess.run(args, check=True, capture_output=True,
                                    text=True)
                self.assertIn("Layout candidates: 1", cp.stdout)
                result = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(result["summary"]["dds_candidates"], 1)
                self.assertEqual(len(result["containers"]), 1)
                self.assertNotIn(str(root), json.dumps(result))
                output.unlink()


if __name__ == "__main__":
    unittest.main()
