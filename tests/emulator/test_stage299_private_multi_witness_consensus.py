"""Stage299 tests: different sources collectively resolve ambiguous layouts."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.foj_stage292_synthetic_gtf_dds_roundtrip import generate_fixture
from tools.foj_stage297_private_tile_reference_gate import _morton
from tools.foj_stage298_inverse_tile_ambiguity import HYPOTHESES
from tools.foj_stage299_private_multi_witness_consensus import (
    MANIFEST_SCHEMA, MIN_CASES, MAX_CASES, _no_duplicate_object,
    audit, consensus, main, match_mask, read_manifest,
)


def invented(name, *, tile=8, order="morton", channel="bgra"):
    w=h=16
    ref=bytearray()
    for y in range(h):
        for x in range(w):
            if name=="spatial":
                v=(9+17*x+31*y+(x*y)%13)&255
                rgba=(v,v,v,255)
            elif name=="spatial2":
                v=(39+11*x+53*y+x*x)&255
                rgba=(v,v,v,(x*37+y*11)&255)
            elif name=="color":
                rgba=(19,41,207,255)
            elif name=="flatgray":
                rgba=(91,91,91,255)
            elif name=="flatgray2":
                rgba=(130,130,130,255)
            elif name=="flatgray3":
                rgba=(11,11,11,255)
            elif name=="broken":
                rgba=((x*29+y*17)&255,(x*7+y*23)&255,
                      (x*11+y*3)&255,255)
            else:
                raise ValueError("unknown test pattern")
            ref.extend(rgba)
    blocks = bytearray(b"\xB7" * (w*h*4))
    tx=w//tile
    for y in range(h):
        for x in range(w):
            lx,ly=x%tile,y%tile
            block=(y//tile)*tx+x//tile
            inside=(ly*tile+lx if order=="raster"
                    else _morton(lx,ly,tile.bit_length()-1))
            at=(block*tile*tile+inside)*4
            r,g,b,a=ref[(y*w+x)*4:(y*w+x)*4+4]
            blocks[at:at+4]=bytes((r,g,b,a)) if channel=="rgba" else bytes((b,g,r,a))
    header=bytearray(generate_fixture(16,16,1,False)[:128])
    header[36]=0x85
    struct.pack_into(">I",header,20,len(blocks))
    struct.pack_into(">I",header,48,w*4)
    return bytes(header)+bytes(blocks),bytes(ref)


def digest(data):
    return hashlib.sha256(data).hexdigest().encode("ascii")


class MultiWitnessConsensusTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        base=Path(folder.name)
        self.root=base
        self.source=base/"source"
        self.owners=base/"owner-digest"
        self.references=base/"rgba-digest"
        self.manifests=base/"manifests"
        for path in (self.source,self.owners,self.references,self.manifests):
            path.mkdir()
        self.manifest_file="owner-cases.json"
        self.cases=[]
        for name in ("spatial","color","spatial2"):
            self.add_case(name)
        self.write_manifest()

    def add_case(self, pattern, *, tile=8, order="morton", channel="bgra"):
        idx=len(self.cases)
        raw,rgba=invented(pattern,tile=tile,order=order,channel=channel)
        rel=f"confidential-asset-{idx}.bin"
        own=f"expected-{idx}.sha256"
        ref=f"rgba-{idx}.sha256"
        (self.source/rel).write_bytes(raw)
        for root,filename,data in ((self.owners,own,raw),(self.references,ref,rgba)):
            file=root/filename
            file.write_text(hashlib.sha256(data).hexdigest()+"\n")
            file.chmod(0o600)
        self.cases.append({"source":rel,"source_digest":own,
                           "reference_digest":ref})

    def write_manifest(self, *, data=None):
        payload={"schema":MANIFEST_SCHEMA,"cases":self.cases} if data is None else data
        file=self.manifests/self.manifest_file
        file.write_text(json.dumps(payload))
        file.chmod(0o600)

    def inspect(self):
        return audit(self.source,self.owners,self.references,
                     self.manifests,self.manifest_file)

    def test_several_individually_ambiguous_witnesses_resolve_unique_consensus(self):
        marks=[]
        for c in self.cases:
            raw=(self.source/c["source"]).read_bytes()
            reference=(self.references/c["reference_digest"]).read_text().strip().encode()
            marks.append(match_mask(raw,reference))
        self.assertEqual(marks[0].bit_count(),2)  # grayscale: channel unknown
        self.assertEqual(marks[1].bit_count(),4)  # solid RGB: spatial unknown
        self.assertEqual(marks[2].bit_count(),2)
        result=consensus(tuple(marks))
        self.assertEqual(result["common_layout_hypotheses"],1)
        self.assertEqual(result["consensus"],
                         {"tile_size":8,"within_tile_order":"morton","channel_order":"bgra"})
        self.assertEqual(result["individually_ambiguous_witnesses"],3)
        self.assertFalse(result["conversion_authorized"])

    def test_private_three_independent_sources_and_refs(self):
        result=self.inspect()
        self.assertEqual(result["independent_cases"],3)
        self.assertTrue(result["each_reference_matched_at_least_one_layout"])
        self.assertFalse(result["original_ps3_format_verified"])
        self.assertFalse(result["original_game_resource_provenance_verified"])

    def test_wrong_texture_layout_across_cases_rejected(self):
        c=self.cases[2]
        raw,rgba=invented("spatial2",tile=4,order="raster",channel="bgra")
        (self.source/c["source"]).write_bytes(raw)
        for root,name,data in (
            (self.owners,c["source_digest"],raw),
            (self.references,c["reference_digest"],rgba)):
            (root/name).write_text(hashlib.sha256(data).hexdigest()+"\n")
        with self.assertRaisesRegex(ValueError,"common layout"):
            self.inspect()

    def test_all_three_flat_gray_textures_remain_ambiguous(self):
        for i,pattern in enumerate(("flatgray","flatgray2","flatgray3")):
            c=self.cases[i]
            raw,rgba=invented(pattern)
            (self.source/c["source"]).write_bytes(raw)
            (self.owners/c["source_digest"]).write_text(hashlib.sha256(raw).hexdigest()+"\n")
            (self.references/c["reference_digest"]).write_text(
                hashlib.sha256(rgba).hexdigest()+"\n")
        with self.assertRaisesRegex(ValueError,"common layout"):
            self.inspect()

    def test_bad_reference_for_one_case_refused(self):
        (self.references/self.cases[1]["reference_digest"]).write_text("0"*64+"\n")
        with self.assertRaisesRegex(ValueError,"no matching"):
            self.inspect()

    def test_source_change_without_owner_digest_refused(self):
        file=self.source/self.cases[0]["source"]
        raw=bytearray(file.read_bytes())
        raw[-4]^=1
        file.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,"digest"):
            self.inspect()

    def test_manifest_fewer_than_three_refused(self):
        self.cases=self.cases[:2]
        self.write_manifest()
        with self.assertRaises(ValueError):
            self.inspect()

    def test_more_than_eight_manifest_entries_refused(self):
        data={"schema":MANIFEST_SCHEMA,"cases":self.cases*3}
        self.write_manifest(data=data)
        with self.assertRaises(ValueError):self.inspect()

    def test_duplicate_case_paths_refused(self):
        self.cases[2]["source"]=self.cases[0]["source"]
        self.write_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_duplicate_owner_digest_filenames_refused(self):
        self.cases[2]["source_digest"]=self.cases[0]["source_digest"]
        self.write_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_duplicate_reference_digest_filenames_refused(self):
        self.cases[2]["reference_digest"]=self.cases[0]["reference_digest"]
        self.write_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_duplicate_source_bytes_across_different_names_refused(self):
        origin=self.cases[0]
        duplicate=self.cases[2]
        data=(self.source/origin["source"]).read_bytes()
        (self.source/duplicate["source"]).write_bytes(data)
        (self.owners/duplicate["source_digest"]).write_text(
            hashlib.sha256(data).hexdigest()+"\n")
        # Bind a consistent pixel reference to the repeated source.
        # Otherwise the earlier witness check (not anti-reuse) would refuse.
        exact=(self.references/origin["reference_digest"]).read_bytes()
        (self.references/duplicate["reference_digest"]).write_bytes(exact)
        with self.assertRaisesRegex(ValueError,"distinct"):
            self.inspect()

    def test_duplicate_canonical_reference_digests_refused(self):
        first=self.cases[0]
        third=self.cases[2]
        contents=(self.references/first["reference_digest"]).read_bytes()
        (self.references/third["reference_digest"]).write_bytes(contents)
        with self.assertRaises((ValueError,)):
            self.inspect()

    def test_manifest_unknown_fields_refused(self):
        self.cases[1]["debug_private_path"]="never output this"
        self.write_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_manifest_case_missing_required_field_refused(self):
        del self.cases[1]["reference_digest"]
        self.write_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_manifest_duplicate_json_object_key_refused(self):
        path=self.manifests/self.manifest_file
        path.write_text('{"schema":"'+MANIFEST_SCHEMA+'","schema":"'+MANIFEST_SCHEMA+'","cases":[]}')
        with self.assertRaises(ValueError):self.inspect()

    def test_manifest_world_readable_refused(self):
        (self.manifests/self.manifest_file).chmod(0o644)
        with self.assertRaises(ValueError):self.inspect()

    def test_manifest_symlink_refused(self):
        file=self.manifests/self.manifest_file
        real=self.manifests/"real"
        real.write_bytes(file.read_bytes())
        file.unlink()
        file.symlink_to(real)
        with self.assertRaises(ValueError):self.inspect()

    def test_manifest_path_traversal_refused(self):
        with self.assertRaises(ValueError):
            audit(self.source,self.owners,self.references,
                  self.manifests,"../"+self.manifest_file)

    def test_invalid_source_relative_escape_refused(self):
        self.cases[0]["source"]="../stolen.dat"
        self.write_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_invalid_digest_path_escape_refused(self):
        self.cases[1]["source_digest"]="nested/sha"
        self.write_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_non_string_paths_refused(self):
        self.cases[1]["source"]=42
        self.write_manifest()
        with self.assertRaises(ValueError):self.inspect()

    def test_private_source_symlink_refused(self):
        file=self.source/self.cases[0]["source"]
        real=self.source/"actual"
        real.write_bytes(file.read_bytes())
        file.unlink()
        file.symlink_to(real)
        with self.assertRaises(ValueError):self.inspect()

    def test_private_digest_is_owner_only(self):
        (self.references/self.cases[0]["reference_digest"]).chmod(0o644)
        with self.assertRaises(ValueError):self.inspect()

    def test_nested_roots_refused(self):
        nested=self.source/"manifest"
        nested.mkdir()
        with self.assertRaises(ValueError):
            audit(self.source,self.owners,self.references,nested,
                  self.manifest_file)

    def test_manifest_requires_private_dedicated_directory(self):
        with self.assertRaises(ValueError):
            audit(self.source,self.owners,self.references,self.source,
                  self.manifest_file)

    def test_invalid_masks_refused(self):
        for masks in ((0,1,1),(1,),(1,1,True),(1,1,256),(1,1,-1)):
            with self.subTest(masks=masks),self.assertRaises(ValueError):
                consensus(masks)

    def test_disjoint_valid_masks_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"common layout"):
            consensus((1,2,4))

    def test_even_if_all_unique_same_layout_no_game_auth(self):
        result=consensus((16,16,16))
        self.assertEqual(result["common_layout_hypotheses"],1)
        self.assertFalse(result["original_ps3_format_verified"])
        self.assertFalse(result["conversion_authorized"])

    def test_report_never_contains_private_ids_or_hashes(self):
        response=json.dumps(self.inspect(),sort_keys=True)
        forbidden=[str(self.root),self.manifest_file]
        for c in self.cases:
            forbidden.extend(c.values())
            forbidden.append((self.owners/c["source_digest"]).read_text().strip())
            forbidden.append((self.references/c["reference_digest"]).read_text().strip())
        for v in forbidden:
            self.assertNotIn(v,response)

    def cli(self):
        return ["--source-root",str(self.source),
                "--source-digest-root",str(self.owners),
                "--reference-digest-root",str(self.references),
                "--manifest-root",str(self.manifests),
                "--manifest-file",self.manifest_file]

    def test_cli_success_no_private_data(self):
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            rc=main(self.cli())
        self.assertEqual(rc,0)
        self.assertEqual(err.getvalue(),"")
        self.assertEqual(json.loads(out.getvalue())["common_layout_hypotheses"],1)
        self.assertNotIn(str(self.root),out.getvalue())

    def test_cli_refusal_never_leaks_private_names(self):
        self.cases[0]["source"]="secret-do-not-print"
        self.write_manifest()
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            rc=main(self.cli())
        self.assertEqual(rc,2)
        self.assertEqual(out.getvalue(),"")
        self.assertNotIn("secret-do-not-print",err.getvalue())
        self.assertNotIn(str(self.root),err.getvalue())


if __name__=="__main__":
    unittest.main()
