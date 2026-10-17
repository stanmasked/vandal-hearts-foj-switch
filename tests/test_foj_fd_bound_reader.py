"""Stage-151 fd-anchor regressions: only synthetic, disposable local files."""
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.foj_fd_bound_reader import (
    open_regular_beneath, read_bounded_prefix,
)
from tools.foj_stability_matrix import synthetic_sample
from tools.foj_texture_probe import inventory, iter_candidate_headers
from tools.foj_texture_relations import build_relations, _read_prefix
from tools.foj_resource_table_hypotheses import infer_tables
from tools.foj_index_column_controls import analyze_index_columns
import tools.foj_fd_bound_reader as anchored
import tools.foj_texture_probe as scanner


SPEC = (4, 8, "little", "ascending", False)


class AnchoredLocalReadTests(unittest.TestCase):
    def test_safe_nested_regular_file_and_byte_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            sub = root / "nested"
            sub.mkdir(parents=True)
            (sub / "sample.bin").write_bytes(b"abc123")
            self.assertEqual(
                read_bounded_prefix(root, "nested/sample.bin", 3), b"abc")
            with open_regular_beneath(root, "nested/sample.bin") as (fp, st):
                self.assertTrue(st.st_size == 6)
                self.assertEqual(fp.read(), b"abc123")
            self.assertEqual(read_bounded_prefix(root, "nested/sample.bin", 0), b"")

    def test_reject_absolute_dotdot_empty_windows_and_non_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in ("../escaped.bin", "/absolute.bin", "a/../c",
                         "a/./c", "a//c", "", r"a\b", "a/\x00b"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    with open_regular_beneath(root, path):
                        pass
            with self.assertRaises(ValueError):
                with open_regular_beneath(root, 3):
                    pass
            with self.assertRaises(ValueError):
                read_bounded_prefix(root, "x.bin", 1024*1024+1)
            with self.assertRaises(ValueError):
                read_bounded_prefix(root, "x.bin", True)

    def test_symlink_root_directory_and_final_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "root"
            root.mkdir()
            (root / "good.bin").write_bytes(b"good")
            (base / "root-link").symlink_to(root, target_is_directory=True)
            (root / "file-link").symlink_to(root / "good.bin")
            (root / "dir-link").symlink_to(root, target_is_directory=True)
            for prefix, relative in (
                (base / "root-link", "good.bin"),
                (root, "file-link"),
                (root, "dir-link/good.bin"),
            ):
                with self.subTest(path=relative), self.assertRaises(ValueError):
                    read_bounded_prefix(prefix, relative, 4)

    def test_fifo_and_directory_are_not_accepted_as_regular(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            with self.assertRaises(ValueError):
                read_bounded_prefix(root, "sub", 8)
            if hasattr(os, "mkfifo"):
                os.mkfifo(root / "named-pipe")
                with self.assertRaises(ValueError):
                    read_bounded_prefix(root, "named-pipe", 8)

    def test_in_place_source_write_detected_before_reader_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "private.bin"
            file.write_bytes(b"known")
            with self.assertRaisesRegex(ValueError, "changed"):
                with open_regular_beneath(root, "private.bin") as (stream, _):
                    self.assertEqual(stream.read(1), b"k")
                    with file.open("r+b") as writer:
                        writer.seek(1)
                        writer.write(b"X")

    def test_final_path_swap_to_symlink_at_open_is_never_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, external = base / "root", base / "external"
            root.mkdir()
            root.joinpath("target.bin").write_bytes(b"safe")
            external.write_bytes(b"secret bytes outside root")
            actual_open = anchored.os.open
            triggered = []

            def swap(path, flags, *args, **kwargs):
                if str(path) == "target.bin" and not triggered:
                    triggered.append(True)
                    (root / "target.bin").rename(root / "saved")
                    (root / "target.bin").symlink_to(external)
                return actual_open(path, flags, *args, **kwargs)

            with patch.object(anchored.os, "open", side_effect=swap):
                with self.assertRaises(ValueError):
                    read_bounded_prefix(root, "target.bin", 128)
            self.assertTrue(triggered)

    def test_intermediate_directory_swap_at_open_is_never_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, external = base / "root", base / "external"
            (root / "inner").mkdir(parents=True)
            external.mkdir()
            (root / "inner" / "target.bin").write_bytes(b"safe")
            (external / "target.bin").write_bytes(b"outside bytes")
            actual_open = anchored.os.open
            triggered = []

            def swap(path, flags, *args, **kwargs):
                if str(path) == "inner" and not triggered:
                    triggered.append(True)
                    (root / "inner").rename(root / "saved")
                    (root / "inner").symlink_to(external, target_is_directory=True)
                return actual_open(path, flags, *args, **kwargs)

            with patch.object(anchored.os, "open", side_effect=swap):
                with self.assertRaises(ValueError):
                    read_bounded_prefix(root, "inner/target.bin", 128)
            self.assertTrue(triggered)

    def test_inventory_rejects_swapped_file_after_lstat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            outside = Path(tmp) / "not-ps3.bin"
            outside.write_bytes(b"outside")
            real_open = scanner.open_regular_at
            triggered = []

            @contextmanager
            def swap_before_descriptor(directory_fd, name):
                if not triggered:
                    triggered.append(True)
                    source = root / "synthetic.bin"
                    source.rename(root / "saved")
                    source.symlink_to(outside)
                with real_open(directory_fd, name) as opened:
                    yield opened

            with patch.object(scanner, "open_regular_at",
                              side_effect=swap_before_descriptor):
                with self.assertRaises(ValueError):
                    inventory(root)
            self.assertTrue(triggered)

    def test_stable_synthetic_dds_chain_still_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            headers = list(iter_candidate_headers(root / "synthetic.bin"))
            self.assertEqual(len(headers), 4)
            scan = inventory(root)
            self.assertEqual(len(scan["candidates"]), 4)
            relations = build_relations(scan, root=root)
            table = infer_tables(relations)
            index = analyze_index_columns(
                table, root=root, prefix_bytes=16384)
            self.assertEqual(table["summary"]["table_hypotheses"], 1)
            self.assertEqual(index["summary"]["index_like_single_field"], 1)

    def test_pointer_reader_rejects_symlink_and_does_not_emit_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            regular = root / "synthetic.bin"
            self.assertEqual(_read_prefix(root, Path("synthetic.bin"), 4),
                             regular.read_bytes()[:4])
            (root / "link.bin").symlink_to(regular)
            with self.assertRaises(ValueError):
                _read_prefix(root, Path("link.bin"), 100)

    def test_reader_rejects_missing_file_without_leaking_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            private = "classified-source-name.bmodel"
            with self.assertRaises(ValueError) as caught:
                read_bounded_prefix(Path(tmp), private, 8)
            self.assertNotIn(private, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
