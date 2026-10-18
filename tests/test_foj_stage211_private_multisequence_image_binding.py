"""Stage211: synthetic-only independent-window source and research image bindings."""
from __future__ import annotations
import contextlib
import copy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_foj_stage205_private_source_png import (
    fixtures,png
)
from tests.test_foj_stage204_private_frame_landmarks import populate
from tools.foj_stage205_private_source_png import prepare
from tools.foj_stage211_private_multisequence_image_binding import (
    SCHEMA,REPORT,read_configuration,verify,main
)
from tools.foj_stage199_private_multiwindow import SCHEMA as WINDOWS_SCHEMA


def construct(folder:Path,n=2,*,replay=False):
    observations={
        "schema":WINDOWS_SCHEMA,
        "motion_independence_declaration":"distinct_actions_operator_declared",
        "observations":[],
    }
    config={"schema":SCHEMA,"windows":[]}
    for i in range(n):
        root=folder/f"window-{i}"
        root.mkdir()
        doc,bindings,source,source_manifest=fixtures(root)
        if i and not replay:
            for j in range(len(doc["frames"])):
                (source/f"frame_{j:03d}.png").write_bytes(
                    png(seed=91+i*23+j*7,color=6 if j%2 else 2)
                )
            source_manifest=prepare(doc,source)
        frames=root/"private-C-wire"
        frames.mkdir()
        populate(frames,doc,bindings)
        src_manifest=root/"PRIVATE-source-manifest.json"
        research_manifest=root/"PRIVATE-research-binding.json"
        src_manifest.write_text(json.dumps(source_manifest))
        research_manifest.write_text(json.dumps(bindings))
        observations["observations"].append(doc)
        config["windows"].append({
            "source_png_dir":str(source),
            "source_manifest":str(src_manifest),
            "research_frames_dir":str(frames),
            "research_binding":str(research_manifest),
        })
    return observations,config


class Stage211PrivateMultiwindowImageTests(unittest.TestCase):
    def test_two_distinct_private_source_image_windows_bind_both_sides(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            r=verify(obs,config)
            self.assertEqual(r["schema"],REPORT)
            self.assertEqual(r["windows_verified"],2)
            self.assertEqual(r["source_png_frames_checked"],6)
            self.assertEqual(r["research_ppm_frames_bound"],6)
            self.assertTrue(r["source_pngs_distinct_across_windows"])
            self.assertEqual(r["diagnosis"],
                             "source_and_research_images_locally_bound_only")
            self.assertFalse(r["window_capture_independence_authenticated"])
            self.assertFalse(r["original_animation_accuracy_verified"])

    def test_three_distinct_capture_sets_can_be_bound(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d),n=3)
            r=verify(obs,config)
            self.assertEqual(r["windows_verified"],3)
            self.assertEqual(r["source_png_frames_checked"],9)
            self.assertTrue(r["source_pngs_distinct_across_windows"])

    def test_identical_png_bytes_across_two_windows_are_not_independent(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d),replay=True)
            r=verify(obs,config)
            self.assertEqual(
                r["diagnosis"],"duplicate_source_png_between_windows"
            )
            self.assertFalse(r["source_pngs_distinct_across_windows"])
            self.assertFalse(r["window_capture_independence_authenticated"])

    def test_changed_source_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            source=Path(config["windows"][1]["source_png_dir"])
            (source/"frame_001.png").write_bytes(png(seed=201,color=6))
            with self.assertRaises(ValueError):
                verify(obs,config)

    def test_swapped_images_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            source=Path(config["windows"][0]["source_png_dir"])
            a,b=source/"frame_000.png",source/"frame_001.png"
            raw_a,raw_b=a.read_bytes(),b.read_bytes()
            a.write_bytes(raw_b)
            b.write_bytes(raw_a)
            with self.assertRaises(ValueError):
                verify(obs,config)

    def test_bad_experimental_frame_annotation_refused(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            obs["observations"][1]["frames"][0]["landmarks"][0][
                "experimental_xy"
            ]=[.01,.02]
            with self.assertRaises(ValueError):
                verify(obs,config)

    def test_deleted_research_image_fails(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            folder=Path(config["windows"][1]["research_frames_dir"])
            (folder/"play_025.ppm").unlink()
            with self.assertRaises(OSError):
                verify(obs,config)

    def test_source_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            folder=Path(config["windows"][0]["source_png_dir"])
            src=folder/"frame_000.png"
            other=folder/"backup.png"
            src.rename(other)
            src.symlink_to(other)
            with self.assertRaises(ValueError):
                verify(obs,config)

    def test_source_metadata_declared_not_proven_original(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            obs["motion_independence_declaration"]="not_established"
            r=verify(obs,config)
            self.assertFalse(r["operator_declared_distinct_actions"])
            self.assertFalse(r["authentic_ps3_gameplay_verified"])

    def test_reject_window_count_and_wrong_schema(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            for bad in (
                {**config,"schema":"not_stage211"},
                {**config,"windows":[]},
                {**config,"windows":config["windows"][:1]},
                {**config,"unknown_private_key":"/home/game.pkg"},
            ):
                with self.subTest(bad=tuple(bad)):
                    with self.assertRaises(ValueError):
                        verify(obs,bad)

    def test_malformed_or_missing_path_members_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            for name in ("source_png_dir","source_manifest",
                         "research_frames_dir","research_binding"):
                bad=copy.deepcopy(config)
                del bad["windows"][0][name]
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        verify(obs,bad)

    def test_output_contains_no_capture_digest_coordinates_or_paths(self):
        with tempfile.TemporaryDirectory() as d:
            obs,config=construct(Path(d))
            report=json.dumps(verify(obs,config))
            for private in (
                d,"sha256","ps3_xy","experimental_xy",
                "landmark_names","frame_000","private-C-wire",
                ".fojrm",".banim",".png",
            ):
                self.assertNotIn(private,report)
            self.assertFalse(json.loads(report)[
                "private_directory_paths_exported"
            ])

    def test_cli_compact_private_manifest_and_path_protection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,config=construct(root)
            observations=root/"operator-source-private.json"
            bindings=root/"secret-image-locations.json"
            observations.write_text(json.dumps(obs))
            bindings.write_text(json.dumps(config))
            stdout=StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main([
                    "--observations",str(observations),
                    "--bindings",str(bindings)
                ]),0)
            self.assertEqual(json.loads(stdout.getvalue())["schema"],REPORT)
            self.assertNotIn(d,stdout.getvalue())
            bindings.write_text('{"schema":"bad"}')
            stderr=StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main([
                    "--observations",str(observations),
                    "--bindings",str(bindings)
                ]),2)
            self.assertNotIn(d,stderr.getvalue())

    def test_recheck_detects_source_replacement_during_multiwindow_run(self):
        from unittest.mock import patch
        from tools.foj_stage211_private_multisequence_image_binding import (
            inspect_sources as original_inspect
        )
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            observations,configuration=construct(root)
            original=Path(configuration["windows"][0]["source_png_dir"])
            first=original/"frame_000.png"
            original_content=first.read_bytes()
            invoked=[0]

            def tampering_check(*args):
                result=original_inspect(*args)
                invoked[0]+=1
                # After window zero was checked once, replace that
                # image while the auditor inspects the other window.
                if invoked[0]==2:
                    first.write_bytes(png(seed=253))
                return result

            with patch(
                "tools.foj_stage211_private_multisequence_image_binding.inspect_sources",
                side_effect=tampering_check,
            ):
                with self.assertRaises(ValueError):
                    verify(observations,configuration)
            self.assertNotEqual(first.read_bytes(),original_content)

    def test_recheck_detects_native_wireframe_replacement_mid_run(self):
        from unittest.mock import patch
        from tools.foj_stage211_private_multisequence_image_binding import (
            inspect_landmarks as original_inspect
        )
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            observations,configuration=construct(root)
            native=Path(configuration["windows"][0]["research_frames_dir"])
            first=native/"initial.ppm"
            invoked=[0]

            def tampering_check(*args):
                result=original_inspect(*args)
                invoked[0]+=1
                if invoked[0]==2:
                    first.write_bytes(b"invalid replacement")
                return result

            with patch(
                "tools.foj_stage211_private_multisequence_image_binding.inspect_landmarks",
                side_effect=tampering_check,
            ):
                with self.assertRaises(ValueError):
                    verify(observations,configuration)

    def test_configuration_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=root/"private.json"
            p.write_text("{}")
            link=root/"linked.json"
            link.symlink_to(p)
            with self.assertRaises(ValueError):
                read_configuration(link)


if __name__=="__main__":
    unittest.main()
