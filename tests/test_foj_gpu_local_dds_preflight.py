"""Generated-only C/Python intake-contract parity for the two Switch GPU slots."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import tools.foj_gpu_local_dds_preflight as preflight


ROOT = Path(__file__).resolve().parents[1]


def put_u32(buf: bytearray, at: int, value: int) -> None:
    struct.pack_into("<I", buf, at, value)


def make_classic_dds(kind: str = "RGBA8", width: int = 8,
                     height: int = 8, mips: int = 1) -> bytes:
    if kind not in ("RGBA8", "BGRA8", "BC1", "BC3"):
        raise ValueError("Only invented supported DDS fixture types")
    is_raw = kind in ("RGBA8", "BGRA8")
    flags = 0x100f if is_raw else 0x81007
    header = bytearray(128)
    header[:4] = b"DDS "
    put_u32(header, 4, 124)
    put_u32(header, 8, flags | (0x20000 if mips > 1 else 0))
    put_u32(header, 12, height)
    put_u32(header, 16, width)
    put_u32(header, 28, mips)
    put_u32(header, 76, 32)
    put_u32(header, 108, 0x401008 if mips > 1 else 0x1000)
    put_u32(header, 80, 0x41 if is_raw else 4)
    if is_raw:
        put_u32(header, 20, width * 4)
        put_u32(header, 88, 32)
        if kind == "RGBA8":
            put_u32(header, 92, 0x000000ff)
            put_u32(header, 100, 0x00ff0000)
        else:
            put_u32(header, 92, 0x00ff0000)
            put_u32(header, 100, 0x000000ff)
        put_u32(header, 96, 0x0000ff00)
        put_u32(header, 104, 0xff000000)
    else:
        put_u32(header, 84, 0x31545844 if kind == "BC1" else 0x35545844)
        put_u32(header, 20, (width // 4) * (height // 4) *
                (8 if kind == "BC1" else 16))
    payload = bytearray()
    w, h = width, height
    for level in range(mips):
        size = (w * h * 4 if is_raw else
                ((w + 3) // 4) * ((h + 3) // 4) *
                (8 if kind == "BC1" else 16))
        payload.extend(bytes([(level * 61 + 13) % 256]) * size)
        w, h = max(1, w // 2), max(1, h // 2)
    return bytes(header + payload)


def matches_preflight(blob: bytes) -> bool:
    try:
        preflight.classify_classic_dds(blob)
        return True
    except ValueError:
        return False


class NativeIntakeContractTests(unittest.TestCase):
    def test_empty_directory_explicitly_maps_to_synthetic_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = preflight.examine_local_slots(Path(tmp))
            self.assertEqual(report["schema"], "foj-gpu-local-dds-preflight-v1")
            self.assertEqual(report["slots"], [
                {"material_slot": 0, "status": "synthetic-fallback"},
                {"material_slot": 1, "status": "synthetic-fallback"},
            ])
            self.assertFalse(report["ps3_resource_format_verified"])
            self.assertFalse(report["nintendo_switch_execution_verified"])
            self.assertNotIn(str(tmp), json.dumps(report))

    def test_two_slot_headers_and_mip_chains(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "material0.dds").write_bytes(make_classic_dds("BGRA8", mips=4))
            (root / "material1.dds").write_bytes(make_classic_dds("BC3", mips=4))
            report = preflight.examine_local_slots(root)
            slots = report["slots"]
            self.assertEqual([x["material_slot"] for x in slots], [0, 1])
            self.assertEqual([x["status"] for x in slots],
                             ["classic-dds-compatible"] * 2)
            self.assertEqual([x["format"] for x in slots],
                             ["BGRA8", "BC3/DXT5"])
            self.assertEqual([x["declared_mip_levels"] for x in slots], [4, 4])
            self.assertTrue(all(x["rgba8_level0_bytes"] == 256 for x in slots))
            self.assertNotIn(str(root), json.dumps(report))
            self.assertNotIn("material0.dds", json.dumps(report))

    def test_one_optional_present_one_uses_synthetic_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "material1.dds").write_bytes(make_classic_dds("BC1"))
            slots = preflight.examine_local_slots(root)["slots"]
            self.assertEqual(slots[0]["status"], "synthetic-fallback")
            self.assertEqual(slots[1]["format"], "BC1/DXT1")

    def test_rejects_existing_unsupported_without_partial_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "material0.dds").write_bytes(make_classic_dds("RGBA8"))
            (root / "material1.dds").write_bytes(b"unsupported")
            with self.assertRaisesRegex(ValueError, "outside the native GPU intake"):
                preflight.examine_local_slots(root)

    def test_no_follow_symlink_directory_and_fifo_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = root / "valid.dds"
            valid.write_bytes(make_classic_dds())
            (root / "material0.dds").symlink_to(valid)
            with self.assertRaisesRegex(ValueError, "not a regular file"):
                preflight.examine_local_slots(root)
            (root / "material0.dds").unlink()
            (root / "material0.dds").mkdir()
            with self.assertRaisesRegex(ValueError, "not a regular file"):
                preflight.examine_local_slots(root)
            (root / "material0.dds").rmdir()
            if hasattr(os, "mkfifo"):
                os.mkfifo(root / "material0.dds")
                with self.assertRaisesRegex(ValueError, "not a regular file"):
                    preflight.examine_local_slots(root)
                (root / "material0.dds").unlink()
            (root / "material0.dds").symlink_to(valid)
            with self.assertRaises(ValueError):
                preflight.examine_local_slots(root / "material0.dds")

    def test_detects_fixed_inode_mutation_between_read_and_final_stat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "material0.dds"
            target.write_bytes(make_classic_dds())
            original = preflight.classify_classic_dds
            def change_same_inode(blob):
                current = target.read_bytes()
                altered = bytearray(current)
                altered[-1] ^= 0x7f
                target.write_bytes(altered)
                return original(blob)
            with patch.object(preflight, "classify_classic_dds",
                              side_effect=change_same_inode):
                with self.assertRaisesRegex(ValueError, "entry changed|changed while"):
                    preflight.examine_local_slots(root)

    def test_existing_file_above_native_cap_is_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (root / "material0.dds").open("wb") as stream:
                stream.truncate(preflight.MAX_FILE_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "outside the native GPU intake"):
                preflight.examine_local_slots(root)

    def test_bad_dds_header_mask_flags_size_and_extra_bytes(self):
        original = make_classic_dds("RGBA8", 8, 8, 1)
        cases = [
            original[:-1],
            original + b"x",
            b"DX10" + original[4:],
            b"invalid",
        ]
        for pos in (4, 8, 12, 16, 20, 24, 28, 76, 80, 84, 88, 92,
                    96, 100, 104, 108, 112, 116, 120, 124):
            blob = bytearray(original)
            put_u32(blob, pos, 0xffffffff)
            cases.append(bytes(blob))
        for case in cases:
            with self.subTest(length=len(case)), self.assertRaises(ValueError):
                preflight.classify_classic_dds(case)
        self.assertTrue(matches_preflight(original))

    def test_native_c_decoder_agrees_with_preflight_on_generated_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exe = root / "native-probe"
            compilation = subprocess.run([
                "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                "-pedantic", "-Igpu",
                "tests/foj_native_dds_contract_probe.c", "gpu/atlas_dds.c",
                "-o", str(exe)],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(compilation.returncode, 0, compilation.stderr)
            base_cases = []
            for kind in ("RGBA8", "BGRA8", "BC1", "BC3"):
                for width, height in ((8, 8), (16, 16), (32, 8)):
                    for mips in (1, 2, 4):
                        base_cases.append(make_classic_dds(
                            kind, width, height, mips))
            trial_cases = list(base_cases)
            seed = make_classic_dds("BC1", 8, 8, 4)
            for pos in (4, 8, 12, 16, 20, 24, 28, 76, 80, 84, 88,
                        92, 96, 100, 104, 108, 112, 116, 120, 124):
                damaged = bytearray(seed)
                put_u32(damaged, pos, 0xffffffff)
                trial_cases.append(bytes(damaged))
            trial_cases.extend((seed[:-1], seed + b"\x00",
                                seed[:64], seed + b"DDS "))
            for i, case in enumerate(trial_cases):
                path = root / "fixture.dds"
                path.write_bytes(case)
                result = subprocess.run([str(exe), str(path)],
                                        capture_output=True, text=True)
                with self.subTest(case=i):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(),
                                     "1" if matches_preflight(case) else "0")
            self.assertGreaterEqual(len(trial_cases), 50)

    def test_cli_success_is_metadata_only_and_new_file_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            (root / "material0.dds").write_bytes(make_classic_dds("RGBA8"))
            output = Path(tmp) / "private-metadata.json"
            cmd = [sys.executable, "-m", "tools.foj_gpu_local_dds_preflight",
                   str(root), "--output", str(output)]
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            published = output.read_text(encoding="utf-8")
            self.assertEqual(json.loads(published),
                             preflight.examine_local_slots(root))
            self.assertNotIn(str(root), published)
            self.assertNotIn(str(root), proc.stdout)
            self.assertNotIn("DDS ", published)
            again = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("must be a new file", again.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), published)

    def test_cli_rejection_is_private_and_no_partial_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            (root / "material0.dds").write_bytes(b"not DDS")
            output = Path(tmp) / "unpublished.json"
            command = [sys.executable, "-m", "tools.foj_gpu_local_dds_preflight",
                       str(root), "--output", str(output)]
            proc = subprocess.run(command, cwd=ROOT,
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(output.exists())
            self.assertNotIn(str(root), proc.stderr)
            self.assertIn("outside the native GPU intake", proc.stderr)


if __name__ == "__main__":
    unittest.main()
