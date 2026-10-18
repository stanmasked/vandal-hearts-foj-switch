"""Stage214: generated-only multi-view production C camera exploration tests."""
from __future__ import annotations

import contextlib
from io import StringIO
import json
import math
from pathlib import Path
import stat
import tempfile
import unittest

from tools.foj_stage201_generated_sd import generated_actors
from tools.foj_stage203_private_actor_evidence import HEADER,IMAGE_BYTES,W,H
from tools.foj_stage214_private_multicamera_preview import (
    SCHEMA,build_contact_sheet,main,parse_view,preview,validate_views
)


class Stage214MultiCamera(unittest.TestCase):
    def assets(self,root):
        rig,a,b=generated_actors()
        files=[root/name for name in ("research.fojrm","a.banim","b.banim")]
        for path,payload in zip(files,(rig,a,b),strict=True):
            path.write_bytes(payload)
        return files

    def test_parse_bounded_float_camera_triples(self):
        self.assertEqual(parse_view("-.65,.40,.86"),(-.65,.4,.86))
        self.assertEqual(
            validate_views([".5,.2,1","-.6,.25,1.25"]),
            ((.5,.2,1.),(-.6,.25,1.25))
        )

    def test_duplicate_missing_or_nonfinite_camera_rejected(self):
        invalid=[
            [],
            ["0,.2,1"],
            ["0,.2,1"]*10,
            ["0,.2,1","0,.2,1"],
            ["nan,.2,1","0,.2,1"],
            ["0,inf,1","0,.2,1"],
            ["0,.2,0","0,.2,1"],
            ["0,.2,1","one,two,three"],
            ["0,.2,1","3.9,.2,1"],
            ["0,.2,1","0,.2,1,5"],
            ["0,.2,1",True],
        ]
        for case in invalid:
            with self.subTest(case=case):
                with self.assertRaises((ValueError,TypeError)):
                    validate_views(case)

    def test_invalid_camera_before_outputs_are_created(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.assets(root)
            destination=root/"never-created"
            with self.assertRaises(ValueError):
                preview(rig,a,b,destination,[".5,.2,1","nan,.2,1"])
            self.assertFalse(destination.exists())

    def test_native_two_views_are_different_and_all_eighteen_frames_exist(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.assets(root)
            dest=root/"two-native-c-views"
            result=preview(rig,a,b,dest,[".5,.2,1","-.65,.4,.86"])
            self.assertEqual(result["schema"],SCHEMA)
            self.assertEqual(result["views_rendered"],2)
            self.assertEqual(result["native_frames_rendered"],18)
            self.assertFalse(result["original_ps3_animation_fidelity_verified"])
            first=dest/"private-camera-frames"/"view-00"
            second=dest/"private-camera-frames"/"view-01"
            self.assertEqual(len(list(first.glob("*.ppm"))),9)
            self.assertEqual(len(list(second.glob("*.ppm"))),9)
            self.assertNotEqual(
                (first/"play_025.ppm").read_bytes(),
                (second/"play_025.ppm").read_bytes()
            )
            for folder in (first,second):
                self.assertEqual(
                    (folder/"initial.ppm").read_bytes(),
                    (folder/"reset.ppm").read_bytes()
                )
                self.assertEqual(
                    (folder/"play_025.ppm").read_bytes(),
                    (folder/"paused.ppm").read_bytes()
                )

    def test_sheet_pixels_match_actual_production_C_frame_tiles(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.assets(root)
            dest=root/"selected-views"
            preview(rig,a,b,dest,[".5,.2,1","-.4,.1,1"])
            sheet=(dest/"private-camera-contact-sheet.ppm").read_bytes()
            h=b"P6\n960 320\n255\n"
            self.assertTrue(sheet.startswith(h))
            self.assertEqual(len(sheet),len(h)+2*W*H*3)
            left=(dest/"private-camera-frames"/"view-00"/"play_025.ppm"
                  ).read_bytes()[len(HEADER):]
            right=(dest/"private-camera-frames"/"view-01"/"play_025.ppm"
                   ).read_bytes()[len(HEADER):]
            for y in (0,100,319):
                start=len(h)+y*2*W*3
                self.assertEqual(
                    sheet[start:start+W*3],
                    left[y*W*3:(y+1)*W*3]
                )
                self.assertEqual(
                    sheet[start+W*3:start+2*W*3],
                    right[y*W*3:(y+1)*W*3]
                )

    def test_private_manifest_has_original_game_authenticity_false(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.assets(root)
            folder=root/"private"
            receipt=preview(rig,a,b,folder,[".5,.2,1","-.5,.4,1.05"])
            private=folder/"private-camera-view-index.json"
            doc=json.loads(private.read_text())
            self.assertEqual(doc["schema"],SCHEMA)
            self.assertEqual(len(doc["view_order"]),2)
            self.assertEqual(doc["contact_sheet_width"],960)
            self.assertEqual(doc["contact_sheet_height"],320)
            self.assertFalse(doc["source_game_camera_match_verified"])
            self.assertEqual(stat.S_IMODE(private.stat().st_mode),0o600)
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode),0o700)
            self.assertEqual(
                stat.S_IMODE((folder/"private-camera-contact-sheet.ppm"
                             ).stat().st_mode),0o600
            )
            self.assertNotIn(str(root),json.dumps(receipt))

    def test_three_cameras_sheet_dimensions_and_order_are_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.assets(root)
            result=preview(
                rig,a,None,root/"three",
                [(.5,.2,1),(-.45,.4,.9),(.65,.1,1.3)]
            )
            self.assertEqual(result["native_frames_rendered"],27)
            file=root/"three"/"private-camera-contact-sheet.ppm"
            header=b"P6\n1440 320\n255\n"
            self.assertTrue(file.read_bytes().startswith(header))
            doc=json.loads((root/"three"/"private-camera-view-index.json"
                            ).read_text())
            self.assertEqual(
                [r["view_index"] for r in doc["view_order"]],[0,1,2]
            )
            self.assertTrue(all(
                r["pause_reset_zero_weight_consistent"]
                for r in doc["view_order"]
            ))

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.assets(root)
            dest=root/"already-present"
            dest.mkdir()
            (dest/"keep-private.txt").write_text("preserve")
            with self.assertRaises(ValueError):
                preview(rig,a,b,dest,[".5,.2,1","-.5,.2,1"])
            self.assertEqual(
                (dest/"keep-private.txt").read_text(),"preserve"
            )

    def test_private_cli_status_hides_camera_options_and_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=self.assets(root)
            output=StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([
                    "--rig",str(rig),"--primary",str(a),
                    "--secondary",str(b),
                    "--camera=.5,.2,1",
                    "--camera=-.65,.4,.86",
                    "--output-root",str(root/"cli-bundle"),
                ]),0)
            report=json.loads(output.getvalue())
            self.assertEqual(report["views_rendered"],2)
            self.assertNotIn(str(root),output.getvalue())
            self.assertNotIn("-.65",output.getvalue())
            self.assertFalse(report["source_game_camera_match_verified"])

    def test_corrupt_sheet_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            bad=root/"bad.ppm"
            bad.write_bytes(b"bad")
            with self.assertRaises(ValueError):
                build_contact_sheet([bad,bad],root/"not-a-sheet.ppm")
            self.assertFalse((root/"not-a-sheet.ppm").exists())


if __name__=="__main__":
    unittest.main()
