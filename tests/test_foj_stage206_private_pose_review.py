"""Stage206: invented-only two-sided annotation overlay image tests.

No actual PS3 game footage or user game resources are ever included.
"""
from __future__ import annotations

import contextlib
from io import StringIO
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tests.test_foj_stage205_private_source_png import (
    fixtures,chunk
)
from tests.test_foj_stage204_private_frame_landmarks import (
    populate
)
from tools.foj_stage205_private_source_png import SIGNATURE,png_info
from tools.foj_stage203_private_actor_evidence import conduct,HEADER,W,H
from tools.foj_stage201_generated_sd import generated_actors
from tools.foj_stage204_private_frame_landmarks import WIRE
from tools.foj_stage206_private_pose_review import (
    SCHEMA,COLOR,create_review,mark,main,png_image,rgb_png
)


def setup(root):
    obs,bindings,source,manifest=fixtures(root)
    research=Path(root)/"invented-native-wireframes"
    research.mkdir()
    populate(research,obs,bindings)
    return obs,bindings,source,manifest,research


def encode_filter_variant(which,rgba=False):
    w,h=96,64
    channels=4 if rgba else 3
    prev=bytes(w*channels)
    payload=[]
    for y in range(h):
        actual=bytes((17+y*3+i)%256 for i in range(w*channels))
        result=bytearray()
        for i,current in enumerate(actual):
            left=actual[i-channels] if i>=channels else 0
            above=prev[i]
            diag=prev[i-channels] if i>=channels else 0
            if which==0:
                predictor=0
            elif which==1:
                predictor=left
            elif which==2:
                predictor=above
            elif which==3:
                predictor=(left+above)//2
            else:
                p=left+above-diag
                a,b,c=abs(p-left),abs(p-above),abs(p-diag)
                predictor=left if a<=b and a<=c else above if b<=c else diag
            result.append((current-predictor)&255)
        payload.append(bytes([which])+bytes(result))
        prev=actual
    header=struct.pack(">IIBBBBB",w,h,8,6 if rgba else 2,0,0,0)
    raw=(SIGNATURE+chunk(b"IHDR",header)+
         chunk(b"IDAT",zlib.compress(b"".join(payload)))+
         chunk(b"IEND",b""))
    return raw


class Stage206PrivateReviewTests(unittest.TestCase):
    def test_rgb_png_decoder_supports_all_five_png_filters(self):
        reference=png_image(encode_filter_variant(0))
        for f in range(5):
            with self.subTest(filter=f):
                got=png_image(encode_filter_variant(f))
                self.assertEqual(got[:2],(96,64))
                self.assertEqual(got[2],reference[2])
        self.assertEqual(list(reference[2][:3]),[17,18,19])

    def test_rgba_alpha_is_composited_to_white(self):
        baseline=png_image(encode_filter_variant(0,rgba=True))
        for f in range(1,5):
            self.assertEqual(png_image(encode_filter_variant(f,rgba=True))[2],
                             baseline[2])
        a=20
        self.assertEqual(
            list(baseline[2][:3]),
            [(c*a+255*(255-a)+127)//255 for c in (17,18,19)]
        )

    def test_two_sided_review_writes_six_private_pngs_and_key(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,bindings,source,manifest,research=setup(root)
            destination=root/"owner-only-review"
            result=create_review(
                obs,manifest,source,bindings,research,destination
            )
            self.assertEqual(result["schema"],SCHEMA)
            self.assertEqual(result["review_pair_count"],3)
            self.assertEqual(result["overlays_generated"],6)
            self.assertFalse(result["manually_reviewed_by_human"])
            self.assertFalse(result["source_ps3_gameplay_authenticated"])
            files=sorted(x.name for x in destination.iterdir())
            self.assertEqual(len(files),8)
            self.assertTrue(
                (destination/"PRIVATE_landmark_number_key.json").exists()
            )
            names=json.loads(
                (destination/"PRIVATE_landmark_number_key.json").read_text()
            )["names_by_number"]
            self.assertEqual(names,sorted(names))
            self.assertEqual(len(names),5)

    def test_original_resolution_preserved_and_number_color_drawn(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,bindings,source,manifest,research=setup(root)
            dest=root/"review"
            create_review(obs,manifest,source,bindings,research,dest)
            image=png_image(
                (dest/"source_000_REVIEW_PRIVATE.png").read_bytes()
            )
            self.assertEqual(image[:2],(96,64))
            first=obs["frames"][0]["landmarks"][0]
            x=round(first["ps3_xy"][0]*95)
            y=round(first["ps3_xy"][1]*63)
            self.assertEqual(
                list(image[2][(y*96+x)*3:(y*96+x+1)*3]),
                list(COLOR)
            )

    def test_experimental_frame_not_resized_or_fabricated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,binding,source,manifest,research=setup(root)
            dest=root/"review"
            create_review(obs,manifest,source,binding,research,dest)
            rgb=png_image(
                (dest/"research_000_REVIEW_PRIVATE.png").read_bytes()
            )
            self.assertEqual(rgb[:2],(480,320))
            self.assertFalse(
                json.loads((dest/"PRIVATE_review_status.json").read_text())[
                    "correct_anatomical_landmarks_confirmed"
                ]
            )

    def test_review_fails_closed_on_tampered_source_png(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,binding,source,manifest,research=setup(root)
            (source/"frame_001.png").write_bytes(
                (source/"frame_002.png").read_bytes()
            )
            dest=root/"no-leak"
            with self.assertRaises(ValueError):
                create_review(obs,manifest,source,binding,research,dest)
            self.assertFalse(dest.exists())

    def test_bad_research_annotation_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,binding,source,manifest,research=setup(root)
            obs["frames"][1]["landmarks"][0]["experimental_xy"]=[.04,.94]
            dest=root/"no-partial"
            with self.assertRaises(ValueError):
                create_review(obs,manifest,source,binding,research,dest)
            self.assertFalse(dest.exists())

    def test_missing_research_image_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,binding,source,manifest,research=setup(root)
            (research/"play_025.ppm").unlink()
            dest=root/"empty"
            with self.assertRaises(OSError):
                create_review(obs,manifest,source,binding,research,dest)
            self.assertFalse(dest.exists())

    def test_refuses_to_overwrite_owner_review_images(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,binding,source,manifest,research=setup(root)
            dest=root/"review"
            create_review(obs,manifest,source,binding,research,dest)
            asset=dest/"source_000_REVIEW_PRIVATE.png"
            before=asset.read_bytes()
            with self.assertRaises(ValueError):
                create_review(obs,manifest,source,binding,research,dest)
            self.assertEqual(asset.read_bytes(),before)

    def test_invalid_marker_number_or_bad_rgb_shape_fails(self):
        rgb=bytearray(10*10*3)
        with self.assertRaises(ValueError):
            mark(rgb,10,10,[.5,.5],33)
        with self.assertRaises(ValueError):
            rgb_png(10,10,bytearray(3))

    def test_generated_review_png_decodes_with_stage205_validator(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,binding,source,manifest,research=setup(root)
            dest=root/"review"
            create_review(obs,manifest,source,binding,research,dest)
            for p in dest.glob("*.png"):
                meta=png_info(p.read_bytes())
                self.assertEqual(len(meta["sha256"]),64)

    def test_cli_never_echoes_image_paths_or_landmark_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,binding,source,manifest,research=setup(root)
            annotations=root/"original_private_coordinates.json"
            lock=root/"private_source_hashes.json"
            mapping=root/"secret_anatomical_points.json"
            annotations.write_text(json.dumps(obs))
            lock.write_text(json.dumps(manifest))
            mapping.write_text(json.dumps(binding))
            dest=root/"PRIVATE-review-output"
            out=StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main([
                    "--observations",str(annotations),
                    "--source-manifest",str(lock),
                    "--source-dir",str(source),
                    "--research-bindings",str(mapping),
                    "--research-dir",str(research),
                    "--output-root",str(dest)]),0)
            self.assertNotIn(str(root),out.getvalue())
            self.assertNotIn("head",out.getvalue())
            self.assertNotIn("sha256",out.getvalue())
            self.assertFalse(json.loads(out.getvalue())[
                "camera_or_original_animation_fidelity_verified"
            ])
            error=StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(main([
                    "--observations",str(annotations),
                    "--source-manifest",str(lock),
                    "--source-dir",str(source),
                    "--research-bindings",str(mapping),
                    "--research-dir",str(research),
                    "--output-root",str(dest)]),2)
            self.assertNotIn(str(root),error.getvalue())

    def test_full_stage203_native_c_pipeline_with_visual_review(self):
        # Keep synthetic fixture provenance explicit: generated rig/animations,
        # generated source screenshots and synthetic C-rendered PPM.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,binding,source,manifest,_unused=setup(root)
            rig,a,b=generated_actors()
            assets=[root/n for n in ("rig.fojrm","a.banim","b.banim")]
            for path,payload in zip(assets,(rig,a,b),strict=True):
                path.write_bytes(payload)
            baseline=root/"baseline-native"
            conduct(*assets,baseline)
            # Select actual synthetic C-rig pixels, not artificial crosses.
            for row,label in zip(obs["frames"],binding["frame_labels"]):
                raw=(baseline/"private-frames"/(label+".ppm")).read_bytes()
                pixels=raw[len(HEADER):]
                samples=[
                    (x,y) for y in range(H) for x in range(W)
                    if pixels[(y*W+x)*3:(y*W+x+1)*3]==WIRE
                ]
                self.assertGreater(len(samples),20)
                chosen=[samples[0]]
                while len(chosen)<5:
                    furthest=max(
                        samples,key=lambda p:min(
                            (p[0]-q[0])**2+(p[1]-q[1])**2 for q in chosen)
                    )
                    chosen.append(furthest)
                sorted_marks=sorted(row["landmarks"],key=lambda v:v["id"])
                for mark,(x,y) in zip(sorted_marks,chosen):
                    mark["experimental_xy"]=[x/(W-1),y/(H-1)]
            annotation=root/"synthetic-observations.json"
            lock=root/"synthetic-manifest.json"
            mapping=root/"synthetic-bindings.json"
            annotation.write_text(json.dumps(obs))
            lock.write_text(json.dumps(manifest))
            mapping.write_text(json.dumps(binding))
            final=root/"two-sided-native-private"
            report=conduct(
                *assets,final,observations=annotation,
                frame_bindings=mapping,source_png_dir=source,
                source_png_manifest=lock,review_overlays=True
            )
            self.assertTrue(report["private_two_sided_review_images_created"])
            self.assertEqual(report["private_review_image_pairs"],3)
            self.assertFalse(
                report["original_ps3_correspondences_human_verified"]
            )
            self.assertEqual(len(list(
                (final/"private-two-sided-review").glob("*.png")
            )),6)

    def test_stage203_requires_both_evidence_sides_to_make_overlays(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rig,a,b=generated_actors()
            assets=[root/n for n in ("rig.fojrm","a.banim","b.banim")]
            for path,payload in zip(assets,(rig,a,b),strict=True):
                path.write_bytes(payload)
            dest=root/"no-invented-overlays"
            with self.assertRaises(ValueError):
                conduct(*assets,dest,review_overlays=True)
            self.assertFalse(dest.exists())


if __name__=="__main__":
    unittest.main()
