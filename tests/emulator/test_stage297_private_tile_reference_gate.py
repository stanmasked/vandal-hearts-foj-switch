"""Stage297 invented tile-order and independent private RGBA witness regressions."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.foj_stage292_synthetic_gtf_dds_roundtrip import (
    canonical_rgba, generate_fixture, _levels,
)
from tools.foj_stage297_private_tile_reference_gate import (
    _interpret, _morton, audit, main,
)


def fixture(width=24, height=13, mips=4, tile=8,
            inside="morton", channel="bgra"):
    canonical = canonical_rgba(width, height, mips, False)
    body = bytearray()
    source_pos = 0
    for w,h in _levels(width,height,mips):
        tx,ty = (w+tile-1)//tile,(h+tile-1)//tile
        payload = bytearray(b"\xB7"*(tx*ty*tile*tile*4))
        for y in range(h):
            for x in range(w):
                block=(y//tile)*tx+x//tile
                lx,ly = x%tile,y%tile
                at=(ly*tile+lx if inside=="raster"
                    else _morton(lx,ly,tile.bit_length()-1))
                dest=(block*tile*tile+at)*4
                origin=source_pos+(y*w+x)*4
                r,g,b,a=canonical[origin:origin+4]
                payload[dest:dest+4]=(bytes((r,g,b,a)) if channel=="rgba"
                                       else bytes((b,g,r,a)))
        body.extend(payload)
        source_pos += w*h*4
    assert source_pos == len(canonical)
    header=bytearray(generate_fixture(width,height,mips,False)[:128])
    header[36]=0x85
    struct.pack_into(">I",header,48,((width+tile-1)//tile)*tile*4)
    struct.pack_into(">I",header,20,len(body))
    return bytes(header)+bytes(body)


class TileWitnessTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.src=root/"source"
        self.sums=root/"source-digests"
        self.reference=root/"reference-digests"
        for path in (self.src,self.sums,self.reference):
            path.mkdir()
        self.filename="private-game-asset.bin"
        self.digest="owner.sha256"
        self.refname="pixels.sha256"
        self.width,self.height,self.mips=24,13,4
        self.raw=fixture()
        self.rgba=canonical_rgba(self.width,self.height,self.mips,False)
        self.seal()

    def seal(self,source=None,expected=None):
        if source is not None:self.raw=source
        if expected is not None:self.rgba=expected
        (self.src/self.filename).write_bytes(self.raw)
        for path,name,payload in (
            (self.sums,self.digest,self.raw),
            (self.reference,self.refname,self.rgba)):
            file=path/name
            file.write_text(hashlib.sha256(payload).hexdigest()+"\n")
            file.chmod(0o600)

    def audit(self,tile=8,inside="morton",channel="bgra"):
        return audit(self.src,self.filename,self.sums,self.digest,
                     self.reference,self.refname,
                     tile=tile,in_tile=inside,channel=channel)

    def test_morton_eight_bgra_mip_chain_matches_reference(self):
        report=self.audit()
        self.assertTrue(report["independent_private_rgba_reference_matched"])
        self.assertFalse(report["original_game_texture_conversion_authorized"])
        self.assertFalse(report["original_foj_source_format_verified"])

    def test_raster_eight_bgra_mip_chain(self):
        self.seal(source=fixture(24,13,4,8,"raster","bgra"))
        self.assertTrue(self.audit(8,"raster","bgra")["all_declared_mips_compared"])

    def test_morton_four_bgra_mip_chain(self):
        self.seal(source=fixture(24,13,4,4,"morton","bgra"))
        self.assertTrue(self.audit(4,"morton","bgra")["all_declared_mips_compared"])

    def test_raster_four_rgba_mip_chain(self):
        self.seal(source=fixture(24,13,4,4,"raster","rgba"))
        self.assertTrue(self.audit(4,"raster","rgba")["all_declared_mips_compared"])

    def test_tiny_mip_tail_has_full_tile_allocation(self):
        blob=fixture(8,8,4,8,"morton","bgra")
        # 8x8, 4x4, 2x2, 1x1: four full 8x8 tiles
        self.assertEqual(len(blob),128+4*8*8*4)
        data,levels=_interpret(blob,tile=8,in_tile="morton",channel="bgra")
        self.assertEqual(levels,4)
        self.assertEqual(data,canonical_rgba(8,8,4,False))

    def test_morton_four_covers_all_tile_indices(self):
        self.assertEqual(sorted(_morton(x,y,2) for x in range(4) for y in range(4)),
                         list(range(16)))

    def test_morton_eight_covers_all_tile_indices(self):
        self.assertEqual(sorted(_morton(x,y,3) for x in range(8) for y in range(8)),
                         list(range(64)))

    def test_wrong_tile_size_fails_even_when_owner_digest_matches(self):
        with self.assertRaises(ValueError):self.audit(4,"morton","bgra")

    def test_wrong_within_tile_order_rejected(self):
        with self.assertRaisesRegex(ValueError,"reference"):self.audit(8,"raster","bgra")

    def test_wrong_channel_order_rejected(self):
        with self.assertRaisesRegex(ValueError,"reference"):self.audit(8,"morton","rgba")

    def test_mip_tail_reference_mismatch_rejected(self):
        self.seal(expected=self.rgba[:-4]+b"\x00\x00\x00\x00")
        with self.assertRaisesRegex(ValueError,"reference"):self.audit()

    def test_source_digest_mismatch_rejected(self):
        (self.sums/self.digest).write_text("0"*64+"\n")
        with self.assertRaises(ValueError):self.audit()

    def test_reference_digest_mismatch_rejected(self):
        (self.reference/self.refname).write_text("f"*64+"\n")
        with self.assertRaises(ValueError):self.audit()

    def test_modified_source_byte_rejected(self):
        blob=bytearray(self.raw)
        blob[256]^=3
        (self.src/self.filename).write_bytes(blob)
        with self.assertRaises(ValueError):self.audit()

    def test_unknown_format_refused_even_with_matching_digest(self):
        blob=bytearray(self.raw)
        blob[36]=0xA5
        self.seal(source=bytes(blob))
        with self.assertRaises(ValueError):self.audit()

    def test_bad_pitch_rejected(self):
        blob=bytearray(self.raw)
        struct.pack_into(">I",blob,48,8)
        self.seal(source=bytes(blob))
        with self.assertRaises(ValueError):self.audit()

    def test_source_trailer_rejected_even_with_new_digest(self):
        self.seal(source=self.raw+b"container")
        with self.assertRaises(ValueError):self.audit()

    def test_source_truncated_rejected(self):
        self.seal(source=self.raw[:-1])
        with self.assertRaises(ValueError):self.audit()

    def test_declared_mips_mismatch_rejected(self):
        blob=bytearray(self.raw)
        blob[37]+=1
        self.seal(source=bytes(blob))
        with self.assertRaises(ValueError):self.audit()

    def test_padding_pixel_independent_reference_ignores_padded_tile_cells(self):
        blob=bytearray(self.raw)
        # Final tile contains only the top-left valid mip pixel.
        blob[-1]^=13
        self.seal(source=bytes(blob))
        self.assertTrue(self.audit()["independent_private_rgba_reference_matched"])

    def test_all_channel_alpha_bytes_unpremultiplied(self):
        decoded,count=_interpret(self.raw,tile=8,in_tile="morton",channel="bgra")
        self.assertEqual(count,4)
        self.assertEqual(decoded,self.rgba)
        self.assertIn(128,decoded[3::4])

    def test_symlinked_source_rejected(self):
        src=self.src/self.filename
        real=self.src/"actual"
        real.write_bytes(src.read_bytes())
        src.unlink()
        src.symlink_to(real)
        with self.assertRaises(ValueError):self.audit()

    def test_reference_digest_requires_private_permissions(self):
        (self.reference/self.refname).chmod(0o644)
        with self.assertRaises(ValueError):self.audit()

    def test_nested_roots_rejected(self):
        nested=self.src/"child"
        nested.mkdir()
        with self.assertRaises(ValueError):
            audit(self.src,self.filename,self.sums,self.digest,
                  nested,self.refname,tile=8,in_tile="morton",channel="bgra")

    def test_relative_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.src,"../"+self.filename,self.sums,self.digest,
                  self.reference,self.refname,
                  tile=8,in_tile="morton",channel="bgra")

    def test_invalid_tile_modes_rejected(self):
        for tile,inside,channel in ((16,"morton","bgra"),(True,"morton","bgra"),
                                    (8,"hilbert","bgra"),(8,"morton","argb")):
            with self.subTest(case=(tile,inside,channel)),self.assertRaises(ValueError):
                self.audit(tile,inside,channel)

    def test_no_private_identifiers_or_hashes_in_report(self):
        result=json.dumps(self.audit(),sort_keys=True)
        for forbidden in (self.filename,self.digest,self.refname,
                          hashlib.sha256(self.raw).hexdigest(),
                          hashlib.sha256(self.rgba).hexdigest(),str(self.src)):
            self.assertNotIn(forbidden,result)

    def cli(self):
        return ["--source-root",str(self.src),
                "--relative-file",self.filename,
                "--source-digest-root",str(self.sums),
                "--source-digest-file",self.digest,
                "--reference-digest-root",str(self.reference),
                "--reference-digest-file",self.refname,
                "--tile","8","--in-tile","morton","--channel","bgra"]

    def test_cli_success_no_original_pixels_or_path(self):
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            code=main(self.cli())
        self.assertEqual(code,0)
        self.assertEqual(stderr.getvalue(),"")
        self.assertTrue(json.loads(stdout.getvalue())["independent_private_rgba_reference_matched"])
        self.assertNotIn(self.filename,stdout.getvalue())

    def test_cli_failure_hides_private_paths(self):
        (self.reference/self.refname).write_text("incorrect")
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            code=main(self.cli())
        self.assertEqual(code,2)
        self.assertEqual(stdout.getvalue(),"")
        self.assertNotIn(self.filename,stderr.getvalue())
        self.assertNotIn(str(self.src),stderr.getvalue())


if __name__=="__main__":
    unittest.main()
