"""Stage-165 SD zip assertions with fabricated NRO/DKSH, no game data."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools.foj_stage165_sd_bundle import INPUTS, publish_bundle
from tools.foj_stage162_synthetic_dds import generated_dds


def dummy_nro() -> bytes:
    blob = bytearray(128)
    blob[16:20] = b"NRO0"
    struct.pack_into("<I", blob, 24, 128)
    return bytes(blob)


def dummy_dksh(stage: int) -> bytes:
    blob = bytearray(512)
    struct.pack_into("<6I", blob, 0, 0x48534B44, 24, 256, 256, 24, 1)
    struct.pack_into("<6I", blob, 24, stage, 0, 0, 0, 0, 0)
    return bytes(blob)


def fake_tree(root: Path) -> None:
    for relative, _staged, kind in INPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        value = dummy_nro() if kind == "nro" else dummy_dksh(
            0 if kind == "vertex" else 1)
        path.write_bytes(value)


class Stage165GeneratedBundleTests(unittest.TestCase):
    def test_valid_bundle_has_only_allowlisted_paths_and_safe_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fake_tree(root)
            (root / "PRIVATE-FoJ-PS3.pkg").write_bytes(b"SECRET-PROPRIETARY")
            result = Path(tmp) / "bundle.zip"
            published = publish_bundle(root, result)
            self.assertFalse(published["ps3_assets_included"])
            self.assertFalse(published["switch_hardware_tested"])
            self.assertFalse(published["playable_game"])
            with zipfile.ZipFile(result) as archive:
                actual = set(archive.namelist())
                expected = {
                    "README_STAGE165.txt", "MANIFEST_STAGE165.json",
                    "switch/foj/foj-deko3d-clear-smoke.nro",
                    "switch/foj/foj-deko3d-triangle-research.nro",
                    "switch/foj/gpu/foj_actor.vert.dksh",
                    "switch/foj/gpu/foj_triangle.frag.dksh",
                    "switch/foj/gpu/material0.dds",
                    "switch/foj/gpu/material1.dds",
                }
                self.assertEqual(actual, expected)
                manifest = json.loads(archive.read("MANIFEST_STAGE165.json"))
                self.assertEqual(manifest, published)
                for item in manifest["files"]:
                    name = item["sd_relative_path"]
                    raw = archive.read(name)
                    self.assertEqual(len(raw), item["size_bytes"])
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
                self.assertEqual(archive.read("switch/foj/gpu/material0.dds"),
                                 generated_dds(0))
                self.assertEqual(archive.read("switch/foj/gpu/material1.dds"),
                                 generated_dds(1))
                self.assertNotIn(str(root), archive.read("MANIFEST_STAGE165.json").decode())
                self.assertNotIn(b"SECRET-PROPRIETARY", result.read_bytes())
                self.assertIn(b"NOT TESTED", archive.read("README_STAGE165.txt"))

    def test_binary_zip_reproducible_even_across_fresh_output_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fake_tree(root)
            first = Path(tmp) / "a.zip"
            second = Path(tmp) / "b.zip"
            publish_bundle(root, first)
            publish_bundle(root, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_output_exclusive_and_unchanged_when_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fake_tree(root)
            dest = Path(tmp) / "protected.zip"
            dest.write_bytes(b"PRIVATE-DO-NOT-OVERWRITE")
            with self.assertRaisesRegex(ValueError, "must be new"):
                publish_bundle(root, dest)
            self.assertEqual(dest.read_bytes(), b"PRIVATE-DO-NOT-OVERWRITE")

    def test_missing_and_invalid_input_fail_before_output_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fake_tree(root)
            outfile = Path(tmp) / "archive.zip"
            vertex = root / "gpu/build/foj_actor.vert.dksh"
            vertex.unlink()
            with self.assertRaises(ValueError):
                publish_bundle(root, outfile)
            self.assertFalse(outfile.exists())
            vertex.write_bytes(dummy_dksh(1))
            with self.assertRaises(ValueError):
                publish_bundle(root, outfile)
            self.assertFalse(outfile.exists())
            vertex.write_bytes(dummy_dksh(0))
            nro = root / "build/foj-deko3d-clear-smoke.nro"
            nro.write_bytes(b"not an NRO")
            with self.assertRaises(ValueError):
                publish_bundle(root, outfile)
            self.assertFalse(outfile.exists())

    def test_source_symlink_rejected_and_output_not_touched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fake_tree(root)
            source = root / "gpu/build/foj_actor.vert.dksh"
            replacement = root / "other.dksh"
            source.rename(replacement)
            source.symlink_to(replacement)
            outfile = Path(tmp) / "bundle.zip"
            with self.assertRaises(ValueError):
                publish_bundle(root, outfile)
            self.assertFalse(outfile.exists())

    def test_cli_emits_generic_status_not_private_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fake_tree(root)
            target = Path(tmp) / "bundle.zip"
            command = [
                sys.executable, "-m", "tools.foj_stage165_sd_bundle",
                "--repo-root", str(root), "--output", str(target),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("hardware test NOT performed", first.stdout)
            self.assertNotIn(str(root), first.stdout)
            duplicate = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("must be new", duplicate.stderr)
            self.assertNotIn(str(root), duplicate.stderr)

    def test_archive_internal_paths_are_relative_and_not_parent_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            fake_tree(root)
            output = Path(tmp) / "sd.zip"
            publish_bundle(root, output)
            with zipfile.ZipFile(output) as archive:
                for member in archive.namelist():
                    self.assertFalse(member.startswith("/"))
                    self.assertNotIn("..", Path(member).parts)
                    self.assertFalse(member.endswith("/"))
                    self.assertLessEqual(len(member), 100)


if __name__ == "__main__":
    unittest.main()
