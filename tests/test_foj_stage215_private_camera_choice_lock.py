"""Stage215: invented-source, real native C rig/camera selection lock tests."""
from __future__ import annotations

import contextlib
from io import StringIO
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from tools.foj_stage201_generated_sd import generated_actors
from tools.foj_stage203_private_actor_evidence import conduct,HEADER
from tools.foj_stage214_private_multicamera_preview import preview
from tools.foj_stage215_private_camera_choice_lock import (
    SCHEMA,REPORT,camera_index,preview_witness,lock_choice,
    verify_choice,staged_source_witness,main
)


class Stage215PrivateLockTests(unittest.TestCase):
    def data(self,root):
        rig,a,b=generated_actors()
        files=[root/name for name in ("local-rig.fojrm","a.banim","b.banim")]
        for path,source in zip(files,(rig,a,b),strict=True):
            path.write_bytes(source)
        return files

    def setup_views(self,root):
        assets=self.data(root)
        preview_root=root/"actual-native-preview"
        preview(
            *assets,preview_root,
            [".5,.2,1","-.65,.4,.86",".67,.1,1.15"]
        )
        return assets,preview_root

    def test_real_native_selected_view_matches_subsequent_stage203(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"PRIVATE-camera-choice.json"
            made=lock_choice(cameras,1,lock)
            self.assertTrue(made["operator_camera_choice_locked_privately"])
            self.assertEqual(made["rendered_frames_pinned"],9)
            self.assertEqual(stat.S_IMODE(lock.stat().st_mode),0o600)
            chosen=json.loads(lock.read_text())
            self.assertEqual(chosen["schema"],SCHEMA)
            self.assertEqual(chosen["view_index"],1)
            self.assertFalse(chosen["original_ps3_camera_authenticated"])
            final=root/"private-final-render"
            conduct(
                *assets,final,
                camera_yaw=-.65,camera_pitch=.4,camera_zoom=.86
            )
            ok=verify_choice(cameras,lock,final)
            self.assertEqual(ok["schema"],REPORT)
            self.assertEqual(ok["matched_native_frames"],9)
            self.assertTrue(ok["camera_parameters_exactly_equal"])
            self.assertTrue(
                ok["owner_private_choice_and_final_native_c_frames_exactly_match"]
            )
            self.assertFalse(ok["original_animation_fidelity_verified"])

    def test_final_staged_rig_tamper_rejected_even_if_ppms_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            lock_choice(cameras,1,lock)
            final=root/"correct-final"
            conduct(*assets,final,camera_yaw=-.65,
                    camera_pitch=.4,camera_zoom=.86)
            self.assertTrue(verify_choice(cameras,lock,final)[
                "owner_private_choice_and_final_native_c_frames_exactly_match"
            ])
            rig=final/"private-switch-sd"/"switch/foj/rig/preview.fojrm"
            changed=bytearray(rig.read_bytes())
            changed[-1]^=1
            rig.write_bytes(changed)
            # No re-render: nine pixels still match, but inputs do not.
            with self.assertRaises(ValueError):
                verify_choice(cameras,lock,final)

    def test_preview_staged_primary_tamper_after_lock_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            lock_choice(cameras,1,lock)
            final=root/"final"
            conduct(*assets,final,camera_yaw=-.65,
                    camera_pitch=.4,camera_zoom=.86)
            primary=(cameras/"private-switch-sd"/
                     "switch/foj/anims/preview.banim")
            changed=bytearray(primary.read_bytes())
            changed[-1]^=1
            primary.write_bytes(changed)
            # The witness recomputes a new digest; only verification
            # against the previously written lock can reject drift.
            with self.assertRaises(ValueError):
                verify_choice(cameras,lock,final)

    def test_final_missing_secondary_clip_rejected_with_same_frames(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            lock_choice(cameras,1,lock)
            final=root/"correct-final"
            conduct(*assets,final,camera_yaw=-.65,
                    camera_pitch=.4,camera_zoom=.86)
            second=(final/"private-switch-sd"/
                    "switch/foj/anims/preview_b.banim")
            second.unlink()
            with self.assertRaises(ValueError):
                verify_choice(cameras,lock,final)

    def test_staged_asset_hashes_read_from_one_no_follow_descriptor(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            staged=root/"private-switch-sd"/"switch/foj"
            (staged/"rig").mkdir(parents=True)
            (staged/"anims").mkdir()
            (staged/"rig/preview.fojrm").write_bytes(b"local-synthetic-rig")
            (staged/"anims/preview.banim").write_bytes(
                b"local-synthetic-animation"
            )
            with patch.object(Path,"read_bytes",side_effect=AssertionError(
                "source path must not be reopened through Path.read_bytes"
            )):
                record=staged_source_witness(root)
            self.assertEqual(len(record["rig"]),64)
            self.assertEqual(len(record["primary"]),64)
            self.assertIsNone(record["secondary"])

    def test_staged_symlink_and_fifo_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            staged=root/"private-switch-sd"/"switch/foj"
            (staged/"rig").mkdir(parents=True)
            (staged/"anims").mkdir()
            (staged/"rig/preview.fojrm").write_bytes(b"made-up-rig")
            primary=staged/"anims/preview.banim"
            original=staged/"anims/owner-clip.banim"
            original.write_bytes(b"made-up-primary")
            primary.symlink_to(original)
            with self.assertRaises(ValueError):
                staged_source_witness(root)
            primary.unlink()
            if hasattr(__import__("os"),"mkfifo"):
                __import__("os").mkfifo(primary)
                with self.assertRaises(ValueError):
                    staged_source_witness(root)

    def test_another_camera_does_not_match_locked_selection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            lock_choice(cameras,1,lock)
            wrong=root/"different-view"
            conduct(*assets,wrong,camera_yaw=.5,camera_pitch=.2,
                    camera_zoom=1)
            with self.assertRaises(ValueError):
                verify_choice(cameras,lock,wrong)

    def test_changed_ppm_pixels_cannot_be_accepted_as_same_camera(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            lock_choice(cameras,1,lock)
            final=root/"correct"
            conduct(*assets,final,camera_yaw=-.65,
                    camera_pitch=.4,camera_zoom=.86)
            frame=final/"private-frames"/"play_025.ppm"
            raw=bytearray(frame.read_bytes())
            raw[len(HEADER)+11]=(raw[len(HEADER)+11]+1)%256
            frame.write_bytes(raw)
            with self.assertRaises(ValueError):
                verify_choice(cameras,lock,final)

    def test_changed_preview_contact_sheet_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            lock_choice(cameras,1,lock)
            sheet=cameras/"private-camera-contact-sheet.ppm"
            payload=bytearray(sheet.read_bytes())
            payload[-3]=(payload[-3]+1)%256
            sheet.write_bytes(payload)
            final=root/"native"
            conduct(*assets,final,camera_yaw=-.65,
                    camera_pitch=.4,camera_zoom=.86)
            with self.assertRaises(ValueError):
                verify_choice(cameras,lock,final)

    def test_changed_camera_manifest_with_valid_bound_values_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            lock_choice(cameras,1,lock)
            final=root/"original-locked-research"
            conduct(*assets,final,camera_yaw=-.65,camera_pitch=.4,
                    camera_zoom=.86)
            index=cameras/"private-camera-view-index.json"
            content=json.loads(index.read_text())
            content["view_order"][1]["yaw_radians"]=-.35
            index.write_text(json.dumps(content))
            # A PNG cannot independently certify a physical camera
            # orientation. Comparing the manifest against the
            # PREVIOUSLY LOCKED camera does detect the substitution.
            with self.assertRaises(ValueError):
                verify_choice(cameras,lock,final)

    def test_no_lock_overwrite_and_invalid_view_index(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            _,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            lock_choice(cameras,1,lock)
            raw=lock.read_bytes()
            with self.assertRaises(ValueError):
                lock_choice(cameras,1,lock)
            self.assertEqual(raw,lock.read_bytes())
            for chosen in (-1,3,True,1.0):
                with self.subTest(chosen=chosen):
                    with self.assertRaises(ValueError):
                        preview_witness(cameras,chosen)

    def test_legacy_user_camera_index_order_is_strict(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            _,cameras=self.setup_views(root)
            index=cameras/"private-camera-view-index.json"
            data=json.loads(index.read_text())
            data["view_order"][0],data["view_order"][1]=(
                data["view_order"][1],data["view_order"][0]
            )
            index.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                camera_index(cameras,1)

    def test_strict_failure_for_replaced_research_view_ppm(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            _,cameras=self.setup_views(root)
            chosen=cameras/"private-camera-frames"/"view-01"/"play_025.ppm"
            raw=bytearray(chosen.read_bytes())
            raw[len(HEADER)+11]=(raw[len(HEADER)+11]+1)%256
            chosen.write_bytes(raw)
            with self.assertRaises(ValueError):
                preview_witness(cameras,1)

    def test_private_cli_success_no_paths_pixels_or_digest_leaks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            assets,cameras=self.setup_views(root)
            lock=root/"private-lock.json"
            out=StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main([
                    "--lock","--preview-root",str(cameras),
                    "--lock-file",str(lock),"--view-index","1"
                ]),0)
            self.assertEqual(json.loads(out.getvalue())["schema"],REPORT)
            self.assertNotIn(d,out.getvalue())
            self.assertNotIn("sha256",out.getvalue())
            final=root/"correct-stage203"
            conduct(*assets,final,camera_yaw=-.65,camera_pitch=.4,
                    camera_zoom=.86)
            outcome=StringIO()
            with contextlib.redirect_stdout(outcome):
                self.assertEqual(main([
                    "--verify","--preview-root",str(cameras),
                    "--lock-file",str(lock),
                    "--stage203-root",str(final)
                ]),0)
            self.assertNotIn(d,outcome.getvalue())
            self.assertNotIn("sha256",outcome.getvalue())

    def test_cli_rejects_missing_mode_arguments_without_path_echo(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=root/"private.json"
            err=StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main([
                    "--verify","--preview-root",str(root),
                    "--lock-file",str(path)
                ]),2)
            self.assertNotIn(d,err.getvalue())


if __name__=="__main__":
    unittest.main()
