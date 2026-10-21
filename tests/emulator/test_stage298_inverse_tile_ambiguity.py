"""Stage298 synthetic uniqueness vs ambiguous Morton/raster pixel fixtures."""
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
from tools.foj_stage297_private_tile_reference_gate import _morton
from tools.foj_stage298_inverse_tile_ambiguity import (
    HYPOTHESES, _inverse_reconstruct, evaluate, audit, main,
)


def make_fixture(w=24, h=13, mips=4, tile=8, within="morton", channel="bgra",
                 *, gray=False):
    canonical = (bytes((91,91,91,255))*sum(
        lw*lh for lw,lh in _levels(w,h,mips)) if gray else
        canonical_rgba(w,h,mips,False))
    body=bytearray()
    pixel_at=0
    for lw,lh in _levels(w,h,mips):
        tiles_x,tiles_y=(lw+tile-1)//tile,(lh+tile-1)//tile
        block=bytearray(b"\xCB"*(tiles_x*tiles_y*tile*tile*4))
        for y in range(lh):
            for x in range(lw):
                group=(y//tile)*tiles_x+(x//tile)
                lx,ly=x%tile,y%tile
                inside=(ly*tile+lx if within=="raster"
                        else _morton(lx,ly,tile.bit_length()-1))
                p=pixel_at+(y*lw+x)*4
                r,g,b,a=canonical[p:p+4]
                i=(group*tile*tile+inside)*4
                block[i:i+4] = (bytes((r,g,b,a)) if channel=="rgba"
                                else bytes((b,g,r,a)))
        body.extend(block)
        pixel_at+=lw*lh*4
    head=bytearray(generate_fixture(w,h,mips,False)[:128])
    head[36]=0x85
    struct.pack_into(">I",head,48,((w+tile-1)//tile)*tile*4)
    struct.pack_into(">I",head,20,len(body))
    return bytes(head)+bytes(body), canonical


def private_digest(payload: bytes) -> bytes:
    return hashlib.sha256(payload).hexdigest().encode("ascii")


class Stage298InverseUniqueTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.source=self.root/"source"
        self.source_hash=self.root/"source-digests"
        self.reference=self.root/"reference-digests"
        for d in (self.source,self.source_hash,self.reference):
            d.mkdir()
        self.filename="owner-private-source.bin"
        self.src_digest_name="owner.sha256"
        self.ref_digest_name="witness.sha256"
        self.raw,self.canonical=make_fixture()
        self.save()

    def save(self, raw=None, canonical=None):
        if raw is not None:self.raw=raw
        if canonical is not None:self.canonical=canonical
        (self.source/self.filename).write_bytes(self.raw)
        for root,name,data in (
            (self.source_hash,self.src_digest_name,self.raw),
            (self.reference,self.ref_digest_name,self.canonical),
        ):
            target=root/name
            target.write_text(hashlib.sha256(data).hexdigest()+"\n")
            target.chmod(0o600)

    def inspect(self):
        return audit(self.source,self.filename,self.source_hash,
                     self.src_digest_name,self.reference,self.ref_digest_name)

    def test_eight_hypotheses_have_unique_morton8_bgra_witness(self):
        result=evaluate(self.raw,private_digest(self.canonical))
        self.assertEqual(result["candidate_hypotheses"],8)
        self.assertEqual(result["decision"],"unique_hypothesis")
        self.assertEqual(result["independent_reference_matches"],1)
        self.assertEqual(result["unique_hypothesis"],
                         {"tile":8,"within_tile":"morton","channel_order":"bgra"})
        self.assertFalse(result["real_game_conversion_authorized"])

    def test_each_eight_experimental_layouts_has_unique_gradient_witness(self):
        for tile,within,channel in HYPOTHESES:
            with self.subTest(layout=(tile,within,channel)):
                raw,canonical=make_fixture(24,13,4,tile,within,channel)
                result=evaluate(raw,private_digest(canonical))
                self.assertEqual(result["independent_reference_matches"],1)
                self.assertEqual(result["unique_hypothesis"],
                    {"tile":tile,"within_tile":within,"channel_order":channel})

    def test_reverse_roundtrip_exact_source_bytes_with_padding(self):
        self.assertEqual(
            _inverse_reconstruct(self.raw,self.canonical,
                                 tile=8,in_tile="morton",channel="bgra"),
            self.raw)

    def test_mip_tail_padding_is_preserved_during_inverse(self):
        changed=bytearray(self.raw)
        changed[-1] ^= 83
        result=_inverse_reconstruct(bytes(changed),self.canonical,
                                    tile=8,in_tile="morton",channel="bgra")
        self.assertEqual(result,bytes(changed))
        self.assertNotEqual(result,self.raw)

    def test_inverse_reference_mutation_changes_source_pixels(self):
        modified=bytearray(self.canonical)
        modified[0]^=1
        output=_inverse_reconstruct(self.raw,bytes(modified),
                                    tile=8,in_tile="morton",channel="bgra")
        self.assertNotEqual(output,self.raw)
        self.assertEqual(len(output),len(self.raw))

    def test_inverse_refuses_wrong_canonical_length(self):
        with self.assertRaises(ValueError):
            _inverse_reconstruct(self.raw,self.canonical[:-4],
                                 tile=8,in_tile="morton",channel="bgra")

    def test_inverse_rejects_untrusted_tile_order(self):
        with self.assertRaises(ValueError):
            _inverse_reconstruct(self.raw,self.canonical,tile=16,
                                 in_tile="raster",channel="bgra")

    def test_symmetric_grayscale_is_eight_way_ambiguous(self):
        raw,rgba=make_fixture(16,16,1,8,"raster","bgra",gray=True)
        result=evaluate(raw,private_digest(rgba))
        self.assertEqual(result["decision"],"ambiguous_hypotheses")
        self.assertEqual(result["independent_reference_matches"],8)
        self.assertIsNone(result["unique_hypothesis"])
        self.save(raw,rgba)
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            self.inspect()

    def test_uniform_grayscale_does_not_raise_false_unique_even_if_reversible(self):
        raw,rgba=make_fixture(16,16,1,4,"morton","rgba",gray=True)
        for tile,within,channel in HYPOTHESES:
            rebuilt=_inverse_reconstruct(raw,rgba,tile=tile,
                                         in_tile=within,channel=channel)
            self.assertEqual(rebuilt,raw)
        self.assertEqual(evaluate(raw,private_digest(rgba))[
            "decision"],"ambiguous_hypotheses")

    def test_wrong_reference_returns_no_match_and_audit_refuses(self):
        mismatched=self.canonical[:-4]+b"\x00\x00\x00\x00"
        result=evaluate(self.raw,private_digest(mismatched))
        self.assertEqual(result["decision"],"no_independent_pixel_match")
        self.save(canonical=mismatched)
        with self.assertRaises(ValueError):
            self.inspect()

    def test_altered_base_level_reference_refused(self):
        alternative=bytes((self.canonical[0]^1,))+self.canonical[1:]
        self.save(canonical=alternative)
        with self.assertRaises(ValueError):self.inspect()

    def test_mixed_alpha_is_not_discarded_by_inverse(self):
        self.assertIn(128,self.canonical[3::4])
        self.assertEqual(_inverse_reconstruct(self.raw,self.canonical,
                         tile=8,in_tile="morton",channel="bgra"),self.raw)

    def test_owner_local_success_report_does_not_claim_game_format(self):
        report=self.inspect()
        self.assertTrue(report["separate_reference_hash_matched"])
        self.assertTrue(report["every_matching_candidate_roundtripped"])
        self.assertFalse(report["original_ps3_assets_verified"])
        self.assertFalse(report["real_game_conversion_authorized"])

    def test_independent_source_hash_mismatch_rejected(self):
        (self.source_hash/self.src_digest_name).write_text("0"*64+"\n")
        with self.assertRaises(ValueError):self.inspect()

    def test_private_reference_hash_mismatch_rejected(self):
        (self.reference/self.ref_digest_name).write_text("f"*64+"\n")
        with self.assertRaises(ValueError):self.inspect()

    def test_owner_source_changed_before_audit_rejected(self):
        raw=bytearray(self.raw)
        raw[220]^=1
        (self.source/self.filename).write_bytes(raw)
        with self.assertRaises(ValueError):self.inspect()

    def test_appended_source_bytes_rejected_even_when_digest_updated(self):
        self.save(raw=self.raw+b"data")
        with self.assertRaises(ValueError):self.inspect()

    def test_incorrect_header_format_rejected(self):
        raw=bytearray(self.raw)
        raw[36]=0xA5
        self.save(raw=bytes(raw))
        with self.assertRaises(ValueError):self.inspect()

    def test_incorrect_tile_pitch_rejected(self):
        raw=bytearray(self.raw)
        struct.pack_into(">I",raw,48,1)
        self.save(raw=bytes(raw))
        with self.assertRaises(ValueError):self.inspect()

    def test_truncated_source_rejected(self):
        self.save(raw=self.raw[:-1])
        with self.assertRaises(ValueError):self.inspect()

    def test_corrupt_private_digest_permissions_rejected(self):
        (self.reference/self.ref_digest_name).chmod(0o644)
        with self.assertRaises(ValueError):self.inspect()

    def test_symlinked_source_file_rejected(self):
        path=self.source/self.filename
        real=self.source/"backing"
        real.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(real)
        with self.assertRaises(ValueError):self.inspect()

    def test_symlinked_digest_file_rejected(self):
        path=self.reference/self.ref_digest_name
        real=self.reference/"digest-real"
        real.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(real)
        with self.assertRaises(ValueError):self.inspect()

    def test_nested_root_rejected(self):
        nested=self.source/"nested"
        nested.mkdir()
        with self.assertRaises(ValueError):
            audit(self.source,self.filename,self.source_hash,
                  self.src_digest_name,nested,self.ref_digest_name)

    def test_parent_directory_escape_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.source,"../"+self.filename,self.source_hash,
                  self.src_digest_name,self.reference,self.ref_digest_name)

    def test_empty_source_rejected(self):
        self.save(raw=b"")
        with self.assertRaises(ValueError):self.inspect()

    def test_bad_reference_digest_type_rejected(self):
        with self.assertRaises(ValueError):evaluate(self.raw,b"invalid")
        with self.assertRaises(ValueError):evaluate(bytearray(self.raw),
                                                    private_digest(self.canonical))

    def test_missing_private_reference_rejected(self):
        (self.reference/self.ref_digest_name).unlink()
        with self.assertRaises(ValueError):self.inspect()

    def test_no_private_paths_hashes_or_bytes_in_success_receipt(self):
        receipt=json.dumps(self.inspect(),sort_keys=True)
        for private in (str(self.root),self.filename,self.src_digest_name,
                        self.ref_digest_name,hashlib.sha256(self.raw).hexdigest(),
                        hashlib.sha256(self.canonical).hexdigest()):
            self.assertNotIn(private,receipt)

    def cli(self):
        return ["--source-root",str(self.source),"--relative-file",self.filename,
                "--source-digest-root",str(self.source_hash),
                "--source-digest-file",self.src_digest_name,
                "--reference-digest-root",str(self.reference),
                "--reference-digest-file",self.ref_digest_name]

    def test_cli_success_only_prints_safe_unique_hypothesis(self):
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            status=main(self.cli())
        self.assertEqual(status,0)
        self.assertEqual(err.getvalue(),"")
        self.assertEqual(json.loads(out.getvalue())["decision"],"unique_hypothesis")
        self.assertNotIn(self.filename,out.getvalue())

    def test_cli_ambiguous_evidence_fails_closed_without_names(self):
        raw,rgba=make_fixture(16,16,1,8,"raster","bgra",gray=True)
        self.save(raw,rgba)
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            status=main(self.cli())
        self.assertEqual(status,2)
        self.assertEqual(out.getvalue(),"")
        for secret in (self.filename,str(self.source),
                       hashlib.sha256(raw).hexdigest()):
            self.assertNotIn(secret,err.getvalue())


if __name__ == "__main__":
    unittest.main()
