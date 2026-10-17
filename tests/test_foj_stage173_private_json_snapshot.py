"""Stage 173: only invented private operator JSON and race fixtures.

These checks never attest that a physical Switch executed or displayed frames.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.foj_stage166_hardware_observations import blank_template, read_ledger
from tools.foj_stage170_cpu_visual_alignment import blank_link, read_link


class Stage173PrivateJsonSnapshotTests(unittest.TestCase):
    def cases(self, root):
        return [
            (root / "private-operator-ledger.json", blank_template(), read_ledger),
            (root / "private-cpu-visual-link.json", blank_link(), read_link),
        ]

    def test_valid_blank_operator_inputs_remain_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path, value, reader in self.cases(Path(tmp)):
                with self.subTest(reader=reader.__name__):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    self.assertEqual(reader(path), value)
                    self.assertNotIn("hardware_execution_verified", reader(path))

    def test_symlink_and_fifo_rejected_for_both_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, value, reader in self.cases(root):
                with self.subTest(reader=reader.__name__):
                    target = path.with_suffix(".target")
                    target.write_text(json.dumps(value), encoding="utf-8")
                    path.symlink_to(target)
                    with self.assertRaises(ValueError):
                        reader(path)
                    path.unlink()
                    if hasattr(os, "mkfifo"):
                        os.mkfifo(path)
                        with self.assertRaises(ValueError):
                            reader(path)
                        path.unlink()

    def test_pre_open_regular_inode_replacement_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path, value, reader in self.cases(Path(tmp)):
                with self.subTest(reader=reader.__name__):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    alternate = path.with_suffix(".alternate")
                    alternate.write_text(json.dumps(value), encoding="utf-8")
                    real_open = os.open

                    def swap(requested, flags, *args, **kwargs):
                        if Path(requested) == path:
                            os.replace(alternate, path)
                        return real_open(requested, flags, *args, **kwargs)

                    with patch("tools.foj_stage173_private_json_snapshot.os.open",
                               side_effect=swap):
                        with self.assertRaises(ValueError):
                            reader(path)

    def test_post_open_regular_inode_replacement_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path, value, reader in self.cases(Path(tmp)):
                with self.subTest(reader=reader.__name__):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    alternate = path.with_suffix(".alternate")
                    alternate.write_text(json.dumps(value), encoding="utf-8")
                    real_fdopen = os.fdopen

                    def swap(fd, mode):
                        os.replace(alternate, path)
                        return real_fdopen(fd, mode)

                    with patch("tools.foj_stage173_private_json_snapshot.os.fdopen",
                               side_effect=swap):
                        with self.assertRaises(ValueError):
                            reader(path)

    def test_in_place_edit_between_descriptor_passes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path, value, reader in self.cases(Path(tmp)):
                with self.subTest(reader=reader.__name__):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    real_fdopen = os.fdopen

                    class ModifyOnRewind:
                        def __init__(self, inner):
                            self.inner = inner

                        def __enter__(self):
                            self.inner.__enter__()
                            return self

                        def __exit__(self, *args):
                            return self.inner.__exit__(*args)

                        def fileno(self):
                            return self.inner.fileno()

                        def read(self, size):
                            return self.inner.read(size)

                        def seek(self, pos, whence=0):
                            if pos == 0 and whence == 0:
                                with path.open("r+b") as writer:
                                    writer.seek(0)
                                    writer.write(b"[")
                                    writer.flush()
                            return self.inner.seek(pos, whence)

                    with patch("tools.foj_stage173_private_json_snapshot.os.fdopen",
                               side_effect=lambda fd, mode: ModifyOnRewind(
                                   real_fdopen(fd, mode))):
                        with self.assertRaises(ValueError):
                            reader(path)

    def test_oversize_and_error_privacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, _value, reader in self.cases(root):
                with self.subTest(reader=reader.__name__):
                    path.write_bytes(b"x" * 70000)
                    with self.assertRaises(ValueError) as error:
                        reader(path)
                    self.assertNotIn(str(root), str(error.exception))

    def test_partial_or_duplicate_json_never_promotes_hardware(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path, value, reader in self.cases(Path(tmp)):
                with self.subTest(reader=reader.__name__):
                    path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
                    with self.assertRaises(ValueError):
                        reader(path)
                    path.write_bytes(b'{"schema":NaN}')
                    with self.assertRaises(ValueError):
                        reader(path)


if __name__ == "__main__":
    unittest.main()
