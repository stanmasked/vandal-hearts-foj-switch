"""Stage 176: generated-only downloaded artifact inventory race regressions."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools.foj_stage176_fd_inventory_snapshot import snapshot_inventory
from tools import foj_stage175_downloaded_artifact_audit as audit


class Stage176FdInventorySnapshotTests(unittest.TestCase):
    @staticmethod
    def tiny(root):
        (root / "build").mkdir()
        (root / "gpu/build").mkdir(parents=True)
        (root / "build" / "receipt.json").write_bytes(b"{}")
        (root / "gpu/build" / "fragment.dksh").write_bytes(b"DKSH" + b"\0" * 32)
        return (frozenset({"build/receipt.json", "gpu/build/fragment.dksh"}),
                frozenset({"build", "gpu", "gpu/build"}))

    def test_two_fd_snapshots_are_exact_and_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files, dirs = self.tiny(root)
            first = snapshot_inventory(root, files, dirs)
            second = snapshot_inventory(root, files, dirs)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 5)
            self.assertEqual([r[0] for r in first],
                             sorted(["d:build", "d:gpu", "d:gpu/build",
                                     "f:build/receipt.json", "f:gpu/build/fragment.dksh"]))

    def test_file_mutation_changes_snapshot_even_with_same_name_and_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files, dirs = self.tiny(root)
            first = snapshot_inventory(root, files, dirs)
            p = root / "gpu/build/fragment.dksh"
            st = p.stat()
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
            self.assertNotEqual(first, snapshot_inventory(root, files, dirs))

    def test_root_symlink_and_subfolder_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            files, dirs = self.tiny(root)
            (root.parent / "link").symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                snapshot_inventory(root.parent / "link", files, dirs)
            directory = root / "gpu/build"
            relocated = root / "gpu/relocated"
            directory.rename(relocated)
            directory.symlink_to(relocated, target_is_directory=True)
            with self.assertRaises(ValueError):
                snapshot_inventory(root, files, dirs)

    def test_missing_unknown_and_fifo_entry_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files, dirs = self.tiny(root)
            p = root / "build/receipt.json"
            p.unlink()
            with self.assertRaises(ValueError):
                snapshot_inventory(root, files, dirs)
            p.write_bytes(b"{}")
            extra = root / "build/unlisted.txt"
            extra.write_bytes(b"x")
            with self.assertRaises(ValueError):
                snapshot_inventory(root, files, dirs)
            extra.unlink()
            if hasattr(os, "mkfifo"):
                os.mkfifo(extra)
                with self.assertRaises(ValueError):
                    snapshot_inventory(root, files, dirs)

    def test_exact_directory_swap_between_content_audit_and_final_scan(self):
        from test_foj_stage175_downloaded_artifact_audit import (
            Stage175DownloadedArtifactTests, COMMIT, RUN,
        )
        temp, root = Stage175DownloadedArtifactTests().prepare()
        with temp:
            original_builder = audit.build_five_receipt

            def replace_dir(*args):
                result = original_builder(*args)
                target = root / "gpu/build"
                relocated = root.parent / (root.name + "-relocated")
                target.rename(relocated)
                try:
                    shutil.copytree(relocated, target)
                finally:
                    shutil.rmtree(relocated)
                return result

            with patch.object(audit, "build_five_receipt",
                              side_effect=replace_dir):
                with self.assertRaises(ValueError):
                    audit.verify_download(root, COMMIT, RUN)

    def test_same_contents_modified_metadata_between_scans_rejected(self):
        from test_foj_stage175_downloaded_artifact_audit import (
            Stage175DownloadedArtifactTests, COMMIT, RUN, EXTRA,
        )
        temp, root = Stage175DownloadedArtifactTests().prepare()
        with temp:
            original_builder = audit.build_five_receipt

            def update_mtime(*args):
                result = original_builder(*args)
                p = root / EXTRA[0]
                st = p.stat()
                os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
                return result

            with patch.object(audit, "build_five_receipt",
                              side_effect=update_mtime):
                with self.assertRaises(ValueError):
                    audit.verify_download(root, COMMIT, RUN)


if __name__ == "__main__":
    unittest.main()
