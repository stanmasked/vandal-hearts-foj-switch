"""FD-relative DDS inventory: disposable synthetic resources only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.foj_texture_probe import inventory
from tools.foj_source_coherence_gate import examine
from tools.foj_fd_bound_reader import READ, NOFOLLOW, DIRECTORY
from tools.foj_stability_matrix import synthetic_sample
import tools.foj_texture_probe as scanner

SPEC = (4, 8, "little", "ascending", False)


class FdDirectoryEnumerationTests(unittest.TestCase):
    def test_nested_order_and_old_manifest_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b-sub").mkdir()
            (root / "a-sub").mkdir()
            (root / "z.bin").write_bytes(b"\xff" * 200)
            (root / "a.bin").write_bytes(b"\xff" * 200)
            (root / "b-sub" / "child.bin").write_bytes(b"\xff" * 100)
            (root / "a-sub" / "inner.bin").write_bytes(b"\xff" * 100)
            out = inventory(root)
            self.assertEqual(out["files_scanned"], 4)
            self.assertEqual(out["candidates"], [])
            self.assertEqual(out["skipped_links"], 0)
            self.assertEqual(out["skipped_large"], 0)
            self.assertEqual(out, inventory(root))
            self.assertEqual(out["schema"], "foj-texture-candidates-v1")

    def test_real_synthetic_dds_in_nested_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            sub = root / "nested"
            synthetic_sample(sub, SPEC)
            result = inventory(root)
            self.assertEqual(result["files_scanned"], 1)
            self.assertEqual(
                [x["relative_path"] for x in result["candidates"]],
                ["nested/synthetic.bin"] * 4)
            self.assertEqual(result["skipped_links"], 0)

    def test_known_symlink_directories_and_files_are_counted_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "root"
            root.mkdir()
            outside = base / "external"
            outside.mkdir()
            (outside / "outside.bin").write_bytes(b"external resource")
            (root / "symlink-file").symlink_to(outside / "outside.bin")
            (root / "symlink-dir").symlink_to(outside, target_is_directory=True)
            scan = inventory(root)
            self.assertEqual(scan["files_scanned"], 0)
            self.assertEqual(scan["skipped_links"], 2)
            # The stronger stage-150 gate never silently accepts skips.
            with self.assertRaises(ValueError):
                examine(root)

    def test_root_symlink_does_not_get_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "real"
            root.mkdir()
            (base / "alias").symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                inventory(base / "alias")

    def test_directory_symlink_swap_at_exact_open_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, outside = base / "root", base / "outside"
            (root / "nested").mkdir(parents=True)
            outside.mkdir()
            (root / "nested" / "safe.bin").write_bytes(b"hello")
            (outside / "foreign.bin").write_bytes(b"secret")
            actual_open = scanner.os.open
            triggered = []

            def swap(path, flags, *args, **kwargs):
                if (path == "nested" and "dir_fd" in kwargs and not triggered):
                    triggered.append(True)
                    (root / "nested").rename(root / "old-nested")
                    (root / "nested").symlink_to(
                        outside, target_is_directory=True)
                return actual_open(path, flags, *args, **kwargs)

            with patch.object(scanner.os, "open", side_effect=swap):
                with self.assertRaisesRegex(ValueError, "safely enter"):
                    inventory(root)
            self.assertTrue(triggered)

    def test_directory_replaced_with_regular_file_at_open_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested").mkdir()
            actual_open = scanner.os.open
            triggered = []

            def swap(path, flags, *args, **kwargs):
                if (path == "nested" and "dir_fd" in kwargs and not triggered):
                    triggered.append(True)
                    (root / "nested").rename(root / "former")
                    (root / "nested").write_bytes(b"not a directory")
                return actual_open(path, flags, *args, **kwargs)

            with patch.object(scanner.os, "open", side_effect=swap):
                with self.assertRaises(ValueError):
                    inventory(root)
            self.assertTrue(triggered)

    def test_directory_modified_during_file_read_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "original.bin"
            file.write_bytes(b"\xff" * 64)
            real_scan = scanner._iter_headers_stream
            triggered = []

            def change(stream, **kwargs):
                if not triggered:
                    triggered.append(True)
                    (root / "new.bin").write_bytes(b"extra entry")
                yield from real_scan(stream, **kwargs)

            with patch.object(scanner, "_iter_headers_stream",
                              side_effect=change):
                with self.assertRaisesRegex(ValueError, "directory changed"):
                    inventory(root)
            self.assertTrue(triggered)

    def test_file_path_replaced_after_read_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "original.bin").write_bytes(b"\xff" * 64)
            actual_scan = scanner._iter_headers_stream
            triggered = []

            def replace(stream, **kwargs):
                if not triggered:
                    triggered.append(True)
                    (root / "original.bin").rename(root / "moved.bin")
                    (root / "original.bin").write_bytes(b"\xff" * 64)
                yield from actual_scan(stream, **kwargs)

            with patch.object(scanner, "_iter_headers_stream",
                              side_effect=replace):
                with self.assertRaisesRegex(ValueError, "replaced"):
                    inventory(root)
            self.assertTrue(triggered)

    def test_truncation_and_large_skip_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a-large.bin").write_bytes(b"\xff" * 200)
            (root / "b.bin").write_bytes(b"1")
            (root / "c.bin").write_bytes(b"2")
            limited = inventory(root, max_files=1, max_file_bytes=50)
            self.assertEqual(limited["skipped_large"], 1)
            self.assertEqual(limited["files_scanned"], 1)
            self.assertTrue(limited["scan_truncated_at_file_limit"])
            with self.assertRaisesRegex(ValueError, "bounds"):
                inventory(root, max_files=True)

    def test_many_empty_directories_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(4):
                (root / ("sub-" + str(i))).mkdir()
            with self.assertRaisesRegex(ValueError, "Too many directories"):
                inventory(root, max_files=1)

    def test_special_file_not_opened(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO unsupported on this OS")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.mkfifo(root / "not-regular")
            scan = inventory(root)
            self.assertEqual(scan["skipped_links"], 1)
            self.assertEqual(scan["files_scanned"], 0)


if __name__ == "__main__":
    unittest.main()
