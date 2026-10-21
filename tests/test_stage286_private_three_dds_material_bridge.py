"""Stage286 generated-only regression suite for owner-local three-DDS bridge."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import tools.foj_stage286_private_three_dds_material_bridge as bridge
from tools.foj_stage260_generated_gpu_sd import generated_dds, SHADERS
from tools.foj_stage266_transparency_order import VIOLET, WARM, COOL
from tools.foj_stage273_dynamic_gpu_sd import generated_actor
from tools.foj_stage267_generated_multiblend_sd import generated_three_layer_materials
from test_foj_gpu_local_dds_preflight import make_classic_dds

PROJECT = Path(__file__).resolve().parents[1]


def fake_install_dynamic(root: Path, shaders: Path, case: str) -> dict:
    if case != "original":
        raise ValueError("Wrong synthetic research actor")
    root.mkdir(mode=0o700)
    dest = root / bridge.SUBDIR
    dest.mkdir(mode=0o700, parents=True)
    pieces = {
        bridge.GEOMETRY: generated_actor("original"),
        bridge.MATERIALS: generated_three_layer_materials(),
        bridge.SLOTS[0]: generated_dds((*VIOLET, 128)),
        bridge.SLOTS[1]: generated_dds((*WARM, 128)),
        bridge.SLOTS[2]: generated_dds((*COOL, 255)),
        SHADERS[0]: b"public-test-vertex-dksh-placeholder",
        SHADERS[1]: b"public-test-fragment-dksh-placeholder",
    }
    for name, blob in pieces.items():
        (dest / name).write_bytes(blob)
    return {"generated_only": True}


class PrivateThreeDdsBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "input"  # Invented DDS only, never game data.
        self.source.mkdir()
        self.out = self.base / "PRIVATE-output"
        self.shaders = self.base / "public-shaders"
        self.shaders.mkdir()
        self._write_sources()
        self.patch = patch.object(bridge, "install_dynamic",
                                  side_effect=fake_install_dynamic)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def _write_sources(self):
        for name, color in zip(bridge.SLOTS,
                               ((*VIOLET, 128), (*WARM, 128), (*COOL, 255))):
            (self.source / name).write_bytes(generated_dds(color))

    def _prepare(self):
        return bridge.prepare(self.source, self.shaders, self.out)

    def test_stages_three_exact_dds_and_generated_material_identity(self):
        report = self._prepare()
        self.assertEqual(report["material_slots_accepted"], 3)
        self.assertEqual(report["compatible_formats"],
                         ["RGBA8", "RGBA8", "RGBA8"])
        self.assertFalse(report["ps3_resource_format_verified"])
        self.assertFalse(report["original_foj_material_mapping_verified"])
        self.assertFalse(report["physical_switch_gpu_verified"])
        self.assertEqual(bridge.verify(self.out), report)
        self.assertEqual(
            (self.out / bridge.SUBDIR / bridge.GEOMETRY).read_bytes(),
            generated_actor("original"))
        self.assertEqual(
            (self.out / bridge.SUBDIR / bridge.MATERIALS).read_bytes(),
            generated_three_layer_materials())
        self.assertTrue(all(
            (self.out / bridge.SUBDIR / name).read_bytes() ==
            (self.source / name).read_bytes() for name in bridge.SLOTS))
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.out / bridge.MANIFEST).stat().st_mode & 0o777,
                         0o600)
        self.assertNotIn(str(self.base), json.dumps(report))
        self.assertNotIn("sha256", json.dumps(report).lower())
        self.assertNotIn("material0.dds", json.dumps(report))

    def test_bc1_and_bc3_front_are_accepted_but_rear_stays_explicitly_opaque(self):
        (self.source / "material0.dds").write_bytes(make_classic_dds("BC1"))
        (self.source / "material1.dds").write_bytes(make_classic_dds("BC3"))
        raw = bytearray(make_classic_dds("BGRA8", mips=3))
        raw[131::4] = b"\xff" * len(raw[131::4])
        (self.source / "material2.dds").write_bytes(raw)
        result = self._prepare()
        self.assertEqual(result["compatible_formats"],
                         ["BC1/DXT1", "BC3/DXT5", "BGRA8"])
        self.assertEqual(bridge.verify(self.out), result)

    def test_missing_rear_slot_fails_before_any_output(self):
        (self.source / "material2.dds").unlink()
        with self.assertRaisesRegex(ValueError, "all three"):
            self._prepare()
        self.assertFalse(self.out.exists())

    def test_rear_one_nonopaque_alpha_rejected(self):
        target = self.source / "material2.dds"
        blob = bytearray(target.read_bytes())
        blob[131] = 254
        target.write_bytes(blob)
        with self.assertRaisesRegex(ValueError, "non-opaque"):
            self._prepare()
        self.assertFalse(self.out.exists())

    def test_rear_mipmap_alpha_rejected_too(self):
        target = self.source / "material2.dds"
        blob = bytearray(make_classic_dds("RGBA8", mips=3))
        blob[131::4] = b"\xff" * len(blob[131::4])
        blob[-1] = 254
        target.write_bytes(blob)
        with self.assertRaisesRegex(ValueError, "non-opaque"):
            self._prepare()

    def test_rear_bc1_is_rejected_as_unproven_opaque(self):
        (self.source / "material2.dds").write_bytes(make_classic_dds("BC1"))
        with self.assertRaisesRegex(ValueError, "RGBA8/BGRA8"):
            self._prepare()
        self.assertFalse(self.out.exists())

    def test_source_slot_symlink_and_special_files_rejected(self):
        first = self.source / "material0.dds"
        first.unlink()
        first.symlink_to(self.source / "material1.dds")
        with self.assertRaisesRegex(ValueError, "regular"):
            self._prepare()
        self.assertFalse(self.out.exists())
        first.unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(first)
            with self.assertRaisesRegex(ValueError, "regular"):
                self._prepare()
            first.unlink()

    def test_source_bytes_changed_during_classification_rejected(self):
        target = self.source / "material0.dds"
        original = bridge.classify_classic_dds
        def mutate(blob):
            data = bytearray(target.read_bytes())
            data[-1] ^= 0x11
            target.write_bytes(data)
            return original(blob)
        with patch.object(bridge, "classify_classic_dds", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "changed"):
                self._prepare()
        self.assertFalse(self.out.exists())

    def test_bad_middle_format_rejected_without_partial_staging(self):
        (self.source / "material1.dds").write_bytes(b"not-DDS")
        with self.assertRaises(ValueError):
            self._prepare()
        self.assertFalse(self.out.exists())

    def test_reject_preexisting_output_without_modifying_it(self):
        self.out.mkdir()
        marker = self.out / "do-not-touch"
        marker.write_text("owner data", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "new private directory"):
            self._prepare()
        self.assertEqual(marker.read_text(), "owner data")

    def test_symlink_in_fresh_generated_slot_does_not_write_through(self):
        external = self.base / "outside"
        external.write_bytes(b"do-not-modify")
        def bad_generated(root, shaders, case):
            fake_install_dynamic(root, shaders, case)
            target = root / bridge.SUBDIR / "material0.dds"
            target.unlink()
            target.symlink_to(external)
        with patch.object(bridge, "install_dynamic", side_effect=bad_generated):
            with self.assertRaisesRegex(ValueError, "slot unexpectedly"):
                self._prepare()
        self.assertEqual(external.read_bytes(), b"do-not-modify")
        self.assertFalse(self.out.exists())

    def test_generated_actor_tamper_detected(self):
        self._prepare()
        path = self.out / bridge.SUBDIR / bridge.GEOMETRY
        blob = bytearray(path.read_bytes())
        blob[-1] ^= 0x20
        path.write_bytes(blob)
        with self.assertRaisesRegex(ValueError, "actor bytes changed"):
            bridge.verify(self.out)

    def test_generated_material_mapping_tamper_detected(self):
        self._prepare()
        path = self.out / bridge.SUBDIR / bridge.MATERIALS
        blob = bytearray(path.read_bytes())
        blob[-1] ^= 1
        path.write_bytes(blob)
        with self.assertRaisesRegex(ValueError, "material bindings changed"):
            bridge.verify(self.out)

    def test_staged_dds_tamper_detected(self):
        self._prepare()
        path = self.out / bridge.SUBDIR / "material1.dds"
        blob = bytearray(path.read_bytes())
        blob[-1] ^= 0x01
        path.write_bytes(blob)
        with self.assertRaisesRegex(ValueError, "bound DDS identity"):
            bridge.verify(self.out)

    def test_shader_tamper_detected(self):
        self._prepare()
        path = self.out / bridge.SUBDIR / SHADERS[0]
        path.write_bytes(b"falsified shader")
        with self.assertRaisesRegex(ValueError, "bound file identity"):
            bridge.verify(self.out)

    def test_manifest_authenticity_false_flags_cannot_be_flipped(self):
        self._prepare()
        target = self.out / bridge.MANIFEST
        entry = json.loads(target.read_text())
        entry["original_ps3_resource_identity_verified"] = True
        target.write_text(json.dumps(entry))
        with self.assertRaisesRegex(ValueError, "manifest contract"):
            bridge.verify(self.out)

    def test_unrelated_private_source_names_never_copied_or_printed(self):
        (self.source / "secret-user-file.txt").write_bytes(b"owner private")
        report = self._prepare()
        self.assertEqual(report["material_slots_accepted"], 3)
        self.assertFalse((self.out / "secret-user-file.txt").exists())
        self.assertNotIn("secret-user-file", json.dumps(report))

    def test_reject_tracked_repository_destination(self):
        destination = PROJECT / "stage286-owner-untracked-directory"
        if destination.exists():
            self.skipTest("Only test nonexistent project directory")
        with self.assertRaisesRegex(ValueError, "tracked project path"):
            bridge.prepare(self.source, self.shaders, destination)
        self.assertFalse(destination.exists())

    def test_cli_errors_hide_source_path_and_private_hashes(self):
        command = [sys.executable, "-m",
                   "tools.foj_stage286_private_three_dds_material_bridge",
                   "verify", "--output-root", str(self.base / "missing-private")]
        child = subprocess.run(command, cwd=PROJECT, text=True,
                               capture_output=True, check=False)
        self.assertEqual(child.returncode, 2)
        self.assertNotIn(str(self.base), child.stderr)
        self.assertNotIn("Traceback", child.stderr)
        self.assertIn("No source details published", child.stderr)


if __name__ == "__main__":
    unittest.main()
