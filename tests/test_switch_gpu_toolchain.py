"""Synthetic directory-only tests; no Switch SDK or game required."""
import os
from pathlib import Path
import tempfile
import unittest

from tools.check_switch_gpu_toolchain import inspect_toolchain


FILES = (
    "devkitA64/bin/aarch64-none-elf-gcc",
    "libnx/include/switch.h",
    "libnx/include/deko3d.h",
    "libnx/lib/libnx.a",
    "libnx/lib/libdeko3dd.a",
    "tools/bin/elf2nro",
    "tools/bin/nacptool",
)
EXECUTABLES = {
    "devkitA64/bin/aarch64-none-elf-gcc",
    "tools/bin/elf2nro",
    "tools/bin/nacptool",
}


class GpuToolchainPreflightTests(unittest.TestCase):
    def populate(self, root: Path):
        for filename in FILES:
            path = root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic")
            path.chmod(0o755 if filename in EXECUTABLES else 0o644)

    def test_empty_toolchain_fails_with_clear_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = inspect_toolchain(
                Path(directory), path_lookup=lambda _: None
            )
            self.assertFalse(report["ready_for_compile_attempt"])
            self.assertEqual(len(report["missing_mandatory"]), len(FILES))
            self.assertNotIn("uam", report["missing_mandatory"])
            self.assertFalse(report["checks"]["uam"]["available"])

    def test_all_mandatory_paths_and_shaders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            result = inspect_toolchain(root, path_lookup=lambda _: None)
            self.assertTrue(result["ready_for_compile_attempt"])
            self.assertFalse(result["checks"]["uam"]["available"])
            need_shader = inspect_toolchain(
                root, require_shaders=True, path_lookup=lambda _: None
            )
            self.assertFalse(need_shader["ready_for_compile_attempt"])
            self.assertEqual(need_shader["missing_mandatory"], ["uam"])
            uam = root / "tools/bin/uam"
            uam.write_bytes(b"synthetic")
            uam.chmod(0o755)
            with_uam = inspect_toolchain(
                root, require_shaders=True, path_lookup=lambda _: None
            )
            self.assertTrue(with_uam["ready_for_compile_attempt"])
            self.assertTrue(with_uam["checks"]["uam"]["available"])

    def test_requires_executable_permission_not_just_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            compiler = root / "devkitA64/bin/aarch64-none-elf-gcc"
            compiler.chmod(0o644)
            report = inspect_toolchain(root, path_lookup=lambda _: None)
            self.assertEqual(report["missing_mandatory"],
                             ["aarch64_compiler"])

    def test_custom_devkit_arch_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            alternate = root / "alternative-aarch64"
            (alternate / "bin").mkdir(parents=True)
            binary = alternate / "bin/aarch64-none-elf-gcc"
            binary.write_bytes(b"synthetic")
            binary.chmod(0o755)
            report = inspect_toolchain(root, alternate,
                                       path_lookup=lambda _: None)
            self.assertTrue(report["ready_for_compile_attempt"])
            self.assertEqual(report["devkita64"], str(alternate))


if __name__ == "__main__":
    unittest.main()
