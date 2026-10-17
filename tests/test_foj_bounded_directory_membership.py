"""Stage 153: bounded, privacy-preserving directory enumeration on invented data."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import tools.foj_fd_bound_reader as reader
import tools.foj_texture_probe as scanner
import tools.foj_source_coherence_gate as coherence
from tools.foj_stability_matrix import synthetic_sample

SPEC = (4, 8, "little", "ascending", False)


class BoundedDirectoryTests(unittest.TestCase):
    def test_too_many_entries_are_rejected_before_sorting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(30):
                (root / f"item-{i:03}.bin").write_bytes(b"\xff")
            with self.assertRaisesRegex(ValueError, "entry limit exceeded"):
                scanner.inventory(root, max_dir_entries=16)
            with self.assertRaisesRegex(ValueError, "entry limit exceeded"):
                coherence.snapshot(root, max_dir_entries=16)

    def test_filename_byte_budget_is_enforced_without_leaking_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = "PRIVATE-WITNESS-FILENAME-12345.bin"
            (root / secret).write_bytes(b"x")
            for method in (
                lambda: scanner.inventory(root, max_dir_name_bytes=8),
                lambda: coherence.snapshot(root, max_dir_name_bytes=8),
            ):
                with self.assertRaisesRegex(ValueError, "name budget exceeded") as e:
                    method()
                self.assertNotIn(secret, str(e.exception))

    def test_symlink_entries_count_toward_directory_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "real.bin").write_bytes(b"safe")
            for i in range(5):
                (root / f"link-{i}").symlink_to(root / "real.bin")
            with self.assertRaisesRegex(ValueError, "entry limit exceeded"):
                scanner.inventory(root, max_dir_entries=4)
            with self.assertRaisesRegex(ValueError, "entry limit exceeded"):
                coherence.snapshot(root, max_dir_entries=4)

    def test_unbounded_generator_is_cut_off_before_full_materialization(self):
        seen = []
        class FakeScandir:
            def __enter__(self):
                def entries():
                    for i in range(1000000):
                        seen.append(i)
                        yield SimpleNamespace(name=f"synthetic{i}")
                return entries()
            def __exit__(self, *_):
                return False

        with patch.object(reader.os, "scandir", return_value=FakeScandir()):
            with self.assertRaisesRegex(ValueError, "entry limit exceeded"):
                reader.bounded_directory_names(6, max_entries=3)
        self.assertEqual(seen, [0, 1, 2, 3])

    def test_duplicate_or_unsafe_listing_fails_closed(self):
        class FakeScandir:
            def __init__(self, names):
                self.names = names
            def __enter__(self):
                return (SimpleNamespace(name=n) for n in self.names)
            def __exit__(self, *_):
                return False

        for names, message in (
            (["alpha", "alpha"], "duplicate"),
            (["alpha", "../private.bin"], "Unsafe"),
            ([""], "Unsafe"),
        ):
            with self.subTest(names=names):
                with patch.object(reader.os, "scandir",
                                  return_value=FakeScandir(names)):
                    with self.assertRaisesRegex(ValueError, message):
                        reader.bounded_directory_names(6)

    def test_invalid_limits_and_boolean_values_are_rejected(self):
        for kwargs in (
            {"max_entries": 0}, {"max_entries": True},
            {"max_entries": 100001},
            {"max_name_bytes": -1}, {"max_name_bytes": False},
            {"max_name_bytes": 67108865},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(ValueError, "limits"):
                    reader.bounded_directory_names(0, **kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            for fn in (scanner.inventory, coherence.snapshot):
                with self.subTest(fn=fn):
                    with self.assertRaises(ValueError):
                        fn(Path(tmp), max_dir_entries=True)

    def test_inventory_checks_membership_again_after_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = scanner.bounded_directory_names
            calls = []
            def inconsistent(fd, **kwargs):
                calls.append(True)
                return real(fd, **kwargs) if len(calls) == 1 else ["ghost"]
            with patch.object(scanner, "bounded_directory_names",
                              side_effect=inconsistent):
                with self.assertRaisesRegex(ValueError, "membership changed"):
                    scanner.inventory(root)
            self.assertEqual(len(calls), 2)

    def test_snapshot_checks_membership_again_after_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = coherence.bounded_directory_names
            calls = []
            def inconsistent(fd, **kwargs):
                calls.append(True)
                return real(fd, **kwargs) if len(calls) == 1 else ["phantom"]
            with patch.object(coherence, "bounded_directory_names",
                              side_effect=inconsistent):
                with self.assertRaisesRegex(ValueError, "membership changed"):
                    coherence.snapshot(root)
            self.assertEqual(len(calls), 2)

    def test_stable_nested_pipeline_and_schema_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            source = root / "nested"
            synthetic_sample(source, SPEC)
            inventory = scanner.inventory(root, max_dir_entries=3,
                                          max_dir_name_bytes=100)
            self.assertEqual(inventory["schema"], "foj-texture-candidates-v1")
            self.assertEqual(inventory["files_scanned"], 1)
            self.assertEqual(len(inventory["candidates"]), 4)
            fingerprint, stats = coherence.snapshot(
                root, max_dir_entries=3, max_dir_name_bytes=100)
            self.assertEqual(stats["regular_files"], 1)
            self.assertTrue(fingerprint)
            full = coherence.examine(
                root, max_dir_entries=3, max_dir_name_bytes=100)
            self.assertEqual(full[-1]["status"], "two-snapshots-match")
            self.assertTrue(full[-1]["summary"]["replay_verified"])

    def test_unsuccessful_capture_does_not_publish_partial_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            (root / "a.bin").write_bytes(b"a")
            (root / "b.bin").write_bytes(b"b")
            output = Path(tmp) / "unpublished"
            with self.assertRaisesRegex(ValueError, "entry limit exceeded"):
                coherence.publish(root, output, max_dir_entries=1)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
