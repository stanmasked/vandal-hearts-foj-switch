"""Stage205 entirely invented PNG frames and mock observations; no real PS3 data."""
from __future__ import annotations
import contextlib
from io import StringIO
import json
from pathlib import Path
import os
import stat
import struct
import tempfile
import unittest
import zlib

from tests.test_foj_stage204_private_frame_landmarks import landmarks_and_frames
from tools.foj_stage205_private_source_png import (
    SCHEMA, REPORT, SIGNATURE, png_info, image_info,
    prepare, inspect_sources, main,
)
from tools.foj_stage201_generated_sd import generated_actors
from tools.foj_stage203_private_actor_evidence import conduct


def chunk(name,blob):
    return (
        struct.pack(">I",len(blob))+name+blob+
        struct.pack(">I",zlib.crc32(name+blob)&0xffffffff)
    )


def png(width=96,height=64,seed=0,*,color=2,filter_byte=0,
        duplicate_idat=False,extra=False):
    channel=3 if color==2 else 4
    raw=b"".join(
        bytes([filter_byte])+bytes(
            ((seed+row*3+col)%256 for col in range(width*channel))
        )
        for row in range(height)
    )
    compressed=zlib.compress(raw,level=9)
    ihdr=chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,color,0,0,0))
    idat=chunk(b"IDAT",compressed)
    end=chunk(b"IEND",b"")
    return SIGNATURE+ihdr+idat+(
        chunk(b"tEXt",b"generated=yes") if extra else b""
    )+end


def fixtures(root):
    root=Path(root)
    obs,binding=landmarks_and_frames()
    source=root/"private-source"
    source.mkdir()
    for i in range(3):
        (source/f"frame_{i:03d}.png").write_bytes(
            png(seed=17+i*31,color=6 if i==1 else 2)
        )
    manifest=prepare(obs,source)
    return obs,binding,source,manifest


class Stage205PrivatePNGTests(unittest.TestCase):
    def test_generated_complete_png_integrity_and_dimensions(self):
        self.assertEqual(png_info(png())["width"],96)
        self.assertEqual(png_info(png(color=6,seed=2))["height"],64)
        self.assertEqual(len(png_info(png())["sha256"]),64)

    def test_source_three_pngs_timestamps_and_annotations_are_bound(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            report=inspect_sources(obs,manifest,source)
            self.assertEqual(report["schema"],REPORT)
            self.assertEqual(report["source_png_frames_locally_bound"],3)
            self.assertTrue(
                report["png_bytes_dimensions_timestamps_match_private_manifest"]
            )
            self.assertFalse(report["original_ps3_gameplay_authenticated"])
            self.assertNotIn("sha256",json.dumps(report))

    def test_image_byte_change_is_caught_even_when_dimensions_same(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            (source/"frame_001.png").write_bytes(png(seed=103,color=6))
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,source)

    def test_swapped_frame_capture_fails(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            a,b=source/"frame_000.png",source/"frame_002.png"
            data=a.read_bytes(),b.read_bytes()
            a.write_bytes(data[1])
            b.write_bytes(data[0])
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,source)

    def test_mismatched_time_and_dimensions_fail(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            manifest["frames"][1]["ps3_time_seconds"]+=.09
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,source)
            manifest=prepare(obs,source)
            manifest["frames"][0]["width"]+=1
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,source)

    def test_wrong_filename_and_path_traversal_refused(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            manifest["frames"][0]["file"]="../owner/private.png"
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,source)

    def test_duplicate_source_images_cannot_prove_distinct_frames(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            (source/"frame_001.png").write_bytes(
                (source/"frame_000.png").read_bytes()
            )
            with self.assertRaises(ValueError):
                prepare(obs,source)
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,source)

    def test_symlink_source_file_or_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            frame=source/"frame_000.png"
            backup=source/"backup.png"
            frame.rename(backup)
            frame.symlink_to(backup)
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,source)
            frame.unlink()
            backup.rename(frame)
            fake=Path(d)/"fake-dir"
            fake.symlink_to(source,target_is_directory=True)
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,fake)

    def test_png_rejects_crc_damage_truncation_or_invalid_filter(self):
        for value in (
            png()[:-7], png()[:-1]+b"X",
            png(filter_byte=5),
            png(width=5000),
            png(height=10),
            png(color=0),
            png()+b"evil",
            b"\x89PNG\r\n\x1a\n"+b"A"*200,
        ):
            with self.subTest(size=len(value)):
                with self.assertRaises(ValueError):
                    png_info(value)

    def test_reject_corrupt_zlib_even_if_png_chunk_crc_updated(self):
        invalid=SIGNATURE+chunk(
            b"IHDR",struct.pack(">IIBBBBB",96,64,8,2,0,0,0)
        )+chunk(b"IDAT",b"not-a-compressed-stream")+chunk(b"IEND",b"")
        with self.assertRaises(ValueError):
            png_info(invalid)

    def test_schema_metadata_duplicate_or_wrong_annotation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            for changes in (
                {"schema":"bad"},
                {"source_kind":"unverified_bad_kind"},
                {"some_private_extra":"/dev/owner"},
            ):
                bad={**manifest,**changes}
                with self.subTest(changes=changes):
                    with self.assertRaises(ValueError):
                        inspect_sources(obs,bad,source)
            obs["frames"][0]["landmarks"][0]["id"]=(
                obs["frames"][0]["landmarks"][1]["id"]
            )
            with self.assertRaises(ValueError):
                inspect_sources(obs,manifest,source)

    def test_prepare_manifest_is_owner_only_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            annotated=Path(d)/"source-landmarks.json"
            annotated.write_text(json.dumps(obs))
            output=Path(d)/"original-private-capture-manifest.json"
            summary=StringIO()
            with contextlib.redirect_stdout(summary):
                self.assertEqual(main([
                    "--prepare","--observations",str(annotated),
                    "--capture-dir",str(source),"--manifest",str(output)
                ]),0)
            self.assertNotIn(d,summary.getvalue())
            self.assertNotIn("sha256",summary.getvalue())
            self.assertEqual(stat.S_IMODE(output.stat().st_mode),0o600)
            self.assertEqual(json.loads(output.read_text()),manifest)
            stderr=StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main([
                    "--prepare","--observations",str(annotated),
                    "--capture-dir",str(source),"--manifest",str(output)
                ]),2)
            self.assertNotIn(str(output),stderr.getvalue())

    def test_verify_cli_does_not_print_png_digest_or_private_path(self):
        with tempfile.TemporaryDirectory() as d:
            obs,_,source,manifest=fixtures(d)
            annotation=Path(d)/"operator-annotations.json"
            lock=Path(d)/"manifest.json"
            annotation.write_text(json.dumps(obs))
            lock.write_text(json.dumps(manifest))
            output=StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([
                    "--verify","--observations",str(annotation),
                    "--capture-dir",str(source),"--manifest",str(lock)
                ]),0)
            self.assertNotIn(d,output.getvalue())
            self.assertNotIn(manifest["frames"][0]["sha256"],output.getvalue())
            self.assertFalse(
                json.loads(output.getvalue())["original_ps3_gameplay_authenticated"]
            )

    def test_private_actor_bundle_accepts_source_png_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,_,source,manifest=fixtures(d)
            rig,a,b=generated_actors()
            paths=[root/n for n in ("rig.fojrm","clip_a.banim","clip_b.banim")]
            for path,raw in zip(paths,(rig,a,b),strict=True):
                path.write_bytes(raw)
            annotations=root/"annotations.json"
            lock=root/"capture-manifest.json"
            annotations.write_text(json.dumps(obs))
            lock.write_text(json.dumps(manifest))
            out=root/"private-bundle"
            result=conduct(*paths,out,observations=annotations,
                source_png_manifest=lock,source_png_dir=source)
            self.assertTrue(result["source_png_captures_content_bound"])
            self.assertFalse(result["source_png_original_ps3_gameplay_authenticated"])
            report=json.loads((out/"private-source-png-audit.json").read_text())
            self.assertEqual(report["source_png_frames_locally_bound"],3)

    def test_private_bundle_bad_source_png_is_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,_,source,manifest=fixtures(d)
            rig,a,b=generated_actors()
            paths=[root/n for n in ("rig.fojrm","clip_a.banim","clip_b.banim")]
            for path,raw in zip(paths,(rig,a,b),strict=True):
                path.write_bytes(raw)
            annotations=root/"annotations.json"
            lock=root/"capture-manifest.json"
            annotations.write_text(json.dumps(obs))
            lock.write_text(json.dumps(manifest))
            (source/"frame_002.png").write_bytes(png(seed=72))
            out=root/"should-not-exist"
            with self.assertRaises(ValueError):
                conduct(*paths,out,observations=annotations,
                        source_png_manifest=lock,source_png_dir=source)
            self.assertFalse(out.exists())

    def test_missing_partner_manifest_and_observations_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            obs,_,source,manifest=fixtures(d)
            rig,a,b=generated_actors()
            paths=[root/n for n in ("rig.fojrm","clip_a.banim","clip_b.banim")]
            for path,raw in zip(paths,(rig,a,b),strict=True):
                path.write_bytes(raw)
            out=root/"should-not-exist"
            with self.assertRaises(ValueError):
                conduct(*paths,out,source_png_dir=source)
            with self.assertRaises(ValueError):
                conduct(*paths,out,source_png_dir=source,
                        source_png_manifest=root/"not-there.json")
            self.assertFalse(out.exists())


if __name__=="__main__":
    unittest.main()
