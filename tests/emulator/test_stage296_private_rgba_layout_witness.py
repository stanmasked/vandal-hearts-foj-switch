"""Stage296: invented-only pixel reference and dual private digest tests."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
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
from tools.foj_stage296_private_rgba_layout_witness import (
    _layout, audit, main,
)


def padded_fixture(w=8, h=8, mips=4, block=16):
    source = generate_fixture(w,h,mips,False)
    body = memoryview(source)[128:]
    out = bytearray()
    position = 0
    for lw,lh in _levels(w,h,mips):
        for _ in range(lh):
            row = bytes(body[position:position+lw*4])
            position += lw*4
            out.extend(row)
            out.extend(b"\xD3" * ((-len(row)) % block))
    assert position == len(body)
    header = bytearray(source[:128])
    struct.pack_into(">I", header, 20, len(out))
    return bytes(header)+bytes(out)


class OwnerOnlyLayoutReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.src=self.root/"source"
        self.sums=self.root/"source-hash-private"
        self.reference=self.root/"reference-hash-private"
        for p in (self.src,self.sums,self.reference):
            p.mkdir()
        self.filename="my-private-game-asset.bin"
        self.srcfile=self.src/self.filename
        self.digest_file="owner.sha256"
        self.ref_file="reference.sha256"
        self.width,self.height,self.mips=16,8,3
        self.raw=generate_fixture(self.width,self.height,self.mips,False)
        self.expected=canonical_rgba(self.width,self.height,self.mips,False)
        self.seal()

    def seal(self, source=None, reference=None):
        if source is not None: self.raw=source
        if reference is not None: self.expected=reference
        self.srcfile.write_bytes(self.raw)
        for folder,name,blob in (
            (self.sums,self.digest_file,self.raw),
            (self.reference,self.ref_file,self.expected),
        ):
            p=folder/name
            p.write_text(hashlib.sha256(blob).hexdigest()+"\n")
            p.chmod(0o600)

    def inspect(self, order="bgra", alignment=1):
        return audit(self.src,self.filename,self.sums,self.digest_file,
                     self.reference,self.ref_file,order=order,
                     row_alignment=alignment)

    def test_three_mip_bgra_matches_separate_rgba_digest(self):
        r=self.inspect()
        self.assertTrue(r["pixel_reference_matched"])
        self.assertTrue(r["mip_levels_matched"])
        self.assertFalse(r["source_format_verified"])
        self.assertFalse(r["native_dds_conversion_authorized"])
        self.assertFalse(r["original_ps3_resource_provenance_verified"])

    def test_all_channel_bytes_preserved_in_raw_bgra_interpretation(self):
        actual,n=_layout(self.raw,"bgra",1)
        self.assertEqual(n,self.mips)
        self.assertEqual(actual,self.expected)
        self.assertIn(128,actual[3::4])
        self.assertTrue(any(actual[i]!=actual[i+2] for i in range(0,len(actual),4)))

    def test_wrong_order_fails_even_when_source_digest_valid(self):
        with self.assertRaisesRegex(ValueError,"reference"):
            self.inspect("rgba",1)

    def test_full_mip_chain_is_compared_not_only_base_level(self):
        alternate=self.expected[:-4]+b"\0\0\0\0"
        self.seal(reference=alternate)
        with self.assertRaisesRegex(ValueError,"reference"):
            self.inspect()

    def test_padded_rows_compare_only_actual_pixels(self):
        self.width,self.height,self.mips=8,8,4
        data=padded_fixture()
        ref=canonical_rgba(8,8,4,False)
        self.seal(source=data,reference=ref)
        self.assertTrue(self.inspect("bgra",16)["pixel_reference_matched"])
        with self.assertRaises(ValueError):
            self.inspect("bgra",1)

    def test_padding_bytes_can_vary_without_changing_pixel_witness(self):
        data=bytearray(padded_fixture())
        data[-1]^=1  # mip tail padding, not an RGBA pixel
        self.seal(source=bytes(data),reference=canonical_rgba(8,8,4,False))
        self.assertTrue(self.inspect("bgra",16)["pixel_reference_matched"])

    def test_mismatched_reference_digest_rejected(self):
        p=self.reference/self.ref_file
        p.write_text("0"*64+"\n")
        with self.assertRaises(ValueError):self.inspect()

    def test_mismatched_source_digest_rejected(self):
        p=self.sums/self.digest_file
        p.write_text("f"*64+"\n")
        with self.assertRaises(ValueError):self.inspect()

    def test_source_byte_mutation_is_rejected(self):
        buf=bytearray(self.raw)
        buf[-1]^=1
        self.srcfile.write_bytes(buf)
        with self.assertRaises(ValueError):self.inspect()

    def test_trailing_bytes_rejected_even_if_digest_updated(self):
        self.seal(source=self.raw+b"\0")
        with self.assertRaises(ValueError):self.inspect()

    def test_bad_base_pitch_rejected_even_if_digest_updated(self):
        buf=bytearray(self.raw)
        struct.pack_into(">I",buf,48,1234)
        self.seal(source=bytes(buf))
        with self.assertRaises(ValueError):self.inspect()

    def test_format_not_bgra_hypothesis_rejected(self):
        buf=bytearray(self.raw)
        buf[36]=0x85
        self.seal(source=bytes(buf))
        with self.assertRaises(ValueError):self.inspect()

    def test_declared_mips_changed_rejected(self):
        buf=bytearray(self.raw)
        buf[37]+=1
        self.seal(source=bytes(buf))
        with self.assertRaises(ValueError):self.inspect()

    def test_unsupported_image_size_rejected(self):
        buf=bytearray(self.raw)
        struct.pack_into(">HH",buf,44,264,8)
        self.seal(source=bytes(buf))
        with self.assertRaises(ValueError):self.inspect()

    def test_digest_needs_owner_only_permissions(self):
        (self.reference/self.ref_file).chmod(0o644)
        with self.assertRaises(ValueError):self.inspect()

    def test_reference_digest_symlink_rejected(self):
        p=self.reference/self.ref_file
        real=self.reference/"real"
        real.write_bytes(p.read_bytes())
        p.unlink()
        p.symlink_to(real)
        with self.assertRaises(ValueError):self.inspect()

    def test_source_file_symlink_rejected(self):
        real=self.src/"actual"
        real.write_bytes(self.raw)
        self.srcfile.unlink()
        self.srcfile.symlink_to(real)
        with self.assertRaises(ValueError):self.inspect()

    def test_source_root_and_reference_root_must_be_independent(self):
        with self.assertRaises(ValueError):
            audit(self.src,self.filename,self.sums,self.digest_file,
                  self.src,self.filename,order="bgra",row_alignment=1)

    def test_nested_reference_root_under_source_root_rejected(self):
        nested=self.src/"nested"
        nested.mkdir()
        with self.assertRaises(ValueError):
            audit(self.src,self.filename,self.sums,self.digest_file,
                  nested,self.ref_file,order="bgra",row_alignment=1)

    def test_unknown_modes_and_row_alignments_rejected(self):
        for mode,alignment in (("argb",1),("bgra",8),("bgra",True),
                               ("BGRA",16),("rgba",0)):
            with self.subTest(mode=mode,alignment=alignment),self.assertRaises(ValueError):
                self.inspect(mode,alignment)

    def test_data_without_hypothesized_gft_version_rejected(self):
        buf=bytearray(self.raw)
        buf[0]=0
        self.seal(source=bytes(buf))
        with self.assertRaises(ValueError):self.inspect()

    def test_private_pixel_hash_never_in_report(self):
        rep=json.dumps(self.inspect(),sort_keys=True)
        for forbidden in (self.filename,self.digest_file,self.ref_file,
                          str(self.root),hashlib.sha256(self.raw).hexdigest(),
                          hashlib.sha256(self.expected).hexdigest()):
            self.assertNotIn(forbidden,rep)

    def test_cli_success_is_only_safe_metadata(self):
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            status=main(self.cli())
        self.assertEqual(status,0)
        self.assertEqual(err.getvalue(),"")
        self.assertTrue(json.loads(out.getvalue())["pixel_reference_matched"])
        self.assertNotIn(self.filename,out.getvalue())

    def cli(self):
        return ["--source-root",str(self.src),
                "--relative-file",self.filename,
                "--source-digest-root",str(self.sums),
                "--source-digest-file",self.digest_file,
                "--reference-digest-root",str(self.reference),
                "--reference-digest-file",self.ref_file,
                "--order","bgra","--row-alignment","1"]

    def test_cli_failure_does_not_print_private_source_name(self):
        (self.reference/self.ref_file).write_text("not-a-hash")
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            status=main(self.cli())
        self.assertEqual(status,2)
        self.assertEqual(out.getvalue(),"")
        for secret in (self.filename,str(self.root),self.ref_file):
            self.assertNotIn(secret,err.getvalue())

    def test_truncated_source_and_invalid_empty_source_rejected(self):
        for blob in (self.raw[:-1],b""):
            self.seal(source=blob)
            with self.assertRaises(ValueError):self.inspect()

    def test_invalid_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.src,"../"+self.filename,self.sums,self.digest_file,
                  self.reference,self.ref_file,order="bgra",row_alignment=1)

    def test_opaque_fixture_verifies_without_premultiplication(self):
        self.seal(source=generate_fixture(16,8,3,True),
                  reference=canonical_rgba(16,8,3,True))
        r=self.inspect()
        self.assertTrue(r["pixel_reference_matched"])


if __name__=="__main__":
    unittest.main()
