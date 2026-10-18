"""Stage 201: only invented local fixture files; strict isolated root tests."""
from __future__ import annotations

import contextlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from tools.foj_stage201_generated_sd import (
    SCHEMA, generated_actors, install_generated_sd, main
)
from tools.check_local_rig_clip_set import inspect_clip_set


class Stage201GeneratedSdTests(unittest.TestCase):
    def test_generated_bmodel_banim_are_topology_compatible(self):
        rig,primary,secondary=generated_actors()
        self.assertNotEqual(primary,secondary)
        record=inspect_clip_set(rig,primary,secondary)
        self.assertTrue(record["primary_hierarchy_match"])
        self.assertTrue(record["secondary_hierarchy_match"])
        self.assertEqual(record["bone_count"],2)
        self.assertFalse(record["original_ps3_actor_clip_binding_verified"])

    def test_isolated_neixum_data_root_has_exact_sdmc_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"isolated-data-root"
            report=install_generated_sd(dest)
            self.assertEqual(report["schema"],SCHEMA)
            self.assertEqual(report["generated_clip_count"],2)
            self.assertEqual(report["sd_relative_root"],"sdmc/switch/foj")
            self.assertFalse(report["original_game_assets_used"])
            assets=list((dest/"sdmc").rglob("*"))
            names=sorted(str(p.relative_to(dest/"sdmc")) for p in assets
                         if p.is_file())
            self.assertEqual(names,[
                "switch/foj/anims/preview.banim",
                "switch/foj/anims/preview_b.banim",
                "switch/foj/rig/preview.fojrm",
            ])
            self.assertFalse((dest/"generated-only-fixtures").exists())

    def test_never_overwrite_existing_emulator_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"existing"
            dest.mkdir()
            (dest/"owned.txt").write_text("don't overwrite")
            with self.assertRaises(ValueError):
                install_generated_sd(dest)
            self.assertEqual((dest/"owned.txt").read_text(),"don't overwrite")

    def test_reject_symlink_even_to_nonexistent_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"entry").symlink_to(root/"missing",target_is_directory=True)
            with self.assertRaises(ValueError):
                install_generated_sd(root/"entry")
            self.assertFalse((root/"missing").exists())

    def test_cli_receipt_contains_only_invented_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"sd-state"
            output=StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--data-root",str(dest)]),0)
            doc=json.loads(output.getvalue())
            self.assertEqual(doc["fixture_type"],
                             "generated_only_no_original_ps3_content")
            self.assertNotIn(tmp,output.getvalue())
            self.assertFalse(doc["nexium_guest_fsp_mount_proven"])

    def test_cli_refusal_does_not_echo_private_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"my-confidential-path"
            dest.mkdir()
            stderr=StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["--data-root",str(dest)]),2)
            self.assertNotIn(tmp,stderr.getvalue())
            self.assertNotIn("confidential",stderr.getvalue())


if __name__=="__main__":
    unittest.main()
