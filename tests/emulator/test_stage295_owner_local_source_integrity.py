"""Stage295 synthetic-only integration and private-source failure regressions."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools.foj_stage292_synthetic_gtf_dds_roundtrip import generate_fixture
from tools.foj_stage295_owner_local_source_integrity import (
    _pass, audit, main,
)


class Stage295OwnerLocalIntegrityTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source_root = self.root / "game-inputs"
        self.source_root.mkdir()
        self.digest_root = self.root / "owner-held-digests"
        self.digest_root.mkdir()
        self.relative = "owner-private-texture-candidate.bin"
        self.digest_name = "owner-expected.sha256"
        self.source = self.source_root / self.relative
        self.digest = self.digest_root / self.digest_name
        self.original = generate_fixture(width=16, height=8, mips=3)
        self.source.write_bytes(self.original)
        self.seal(self.original)

    def seal(self, payload: bytes):
        self.digest.write_text(hashlib.sha256(payload).hexdigest() + "\n")
        self.digest.chmod(0o600)

    def inspect(self):
        return audit(self.source_root, self.relative,
                     self.digest_root, self.digest_name)

    def assert_refused(self):
        with self.assertRaises((OSError, TypeError, ValueError)):
            self.inspect()

    def test_synthetic_source_matches_owner_digest_but_not_real_game_provenance(self):
        report = self.inspect()
        self.assertTrue(report["verified_against_owner_supplied_digest"])
        self.assertTrue(report["two_full_passes_on_same_anchored_descriptor"])
        self.assertTrue(report["source_bytes_replayed_unchanged"])
        self.assertTrue(report["synthetic_fixture_marker_seen"])
        self.assertEqual(report["stage294_hypothesis_decision"],
                         "candidate_envelope_consistent_under_unverified_hypothesis")
        self.assertFalse(report["claimed_original_game_origin_verified"])
        self.assertFalse(report["native_dds_conversion_authorized"])

    def test_normal_unclassified_bytes_still_match_without_game_claim(self):
        data = b"synthetic, not an image"*13
        self.source.write_bytes(data)
        self.seal(data)
        report = self.inspect()
        self.assertEqual(report["candidate_class"], "unknown_or_non_texture")
        self.assertFalse(report["source_format_confirmed"])
        self.assertFalse(report["original_ps3_pixels_decoded"])

    def test_digest_mismatch_fails_closed(self):
        self.digest.write_text("0"*64+"\n")
        self.assert_refused()

    def test_changed_source_size_fails_closed(self):
        self.source.write_bytes(self.original[:-1])
        self.assert_refused()

    def test_mutated_source_same_size_fails_closed(self):
        data = bytearray(self.original)
        data[-1] ^= 1
        self.source.write_bytes(data)
        self.assert_refused()

    def test_appended_source_bytes_rejected(self):
        self.source.write_bytes(self.original+b"X")
        self.assert_refused()

    def test_uppercase_digest_is_rejected(self):
        self.digest.write_text(hashlib.sha256(self.original).hexdigest().upper()+"\n")
        self.assert_refused()

    def test_invalid_and_extra_digest_bytes_rejected(self):
        for value in ("broken\n", "f"*64+" extra\n", "a"*63+"\n", "a"*65+"\n"):
            with self.subTest(value=value):
                self.digest.write_text(value)
                self.assert_refused()

    def test_digest_file_world_readable_rejected(self):
        self.digest.chmod(0o644)
        self.assert_refused()

    def test_digest_symlink_rejected(self):
        p = self.digest_root/"real"
        p.write_bytes(self.digest.read_bytes())
        self.digest.unlink()
        self.digest.symlink_to(p)
        self.assert_refused()

    def test_source_symlink_rejected(self):
        p = self.source_root/"real"
        p.write_bytes(self.original)
        self.source.unlink()
        self.source.symlink_to(p)
        self.assert_refused()

    def test_source_nested_symlink_ancestor_rejected(self):
        folder = self.source_root/"real"
        folder.mkdir()
        (folder/"texture").write_bytes(self.original)
        (self.source_root/"alias").symlink_to(folder, target_is_directory=True)
        self.relative="alias/texture"
        self.assert_refused()

    def test_source_root_symlink_rejected(self):
        alias = self.root/"symlinked-root"
        alias.symlink_to(self.source_root, target_is_directory=True)
        with self.assertRaises(ValueError):
            audit(alias, self.relative, self.digest_root, self.digest_name)

    def test_digest_root_symlink_rejected(self):
        alias = self.root/"symlinked-digests"
        alias.symlink_to(self.digest_root, target_is_directory=True)
        with self.assertRaises(ValueError):
            audit(self.source_root, self.relative, alias, self.digest_name)

    def test_digest_inside_source_root_rejected(self):
        self.assert_refused_same_root()

    def assert_refused_same_root(self):
        with self.assertRaises(ValueError):
            audit(self.source_root, self.relative, self.source_root,
                  self.relative)

    def test_relative_source_traversal_rejected(self):
        for relative in ("../game-inputs/"+self.relative, "/tmp/source",
                         "sub/../"+self.relative, "sub\\name"):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                audit(self.source_root, relative, self.digest_root,
                      self.digest_name)

    def test_digest_name_traversal_rejected(self):
        for name in ("../owner-expected.sha256", "/tmp/digest", "a/b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                audit(self.source_root, self.relative, self.digest_root, name)

    def test_no_source_or_digest_identity_in_success_report(self):
        report = json.dumps(self.inspect(), sort_keys=True)
        self.assertNotIn(self.relative, report)
        self.assertNotIn(self.digest_name, report)
        self.assertNotIn(str(self.root), report)
        self.assertNotIn(hashlib.sha256(self.original).hexdigest(), report)
        self.assertNotIn('"width"', report)
        self.assertNotIn('"height"', report)

    def test_cli_success_prints_safe_aggregate_report_only(self):
        out, err = io.StringIO(), io.StringIO()
        argv = ["--source-root",str(self.source_root),
                "--relative-file",self.relative,
                "--digest-root",str(self.digest_root),
                "--digest-file",self.digest_name]
        with redirect_stdout(out), redirect_stderr(err):
            rc = main(argv)
        self.assertEqual(rc, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertTrue(json.loads(out.getvalue())[
            "verified_against_owner_supplied_digest"])
        for forbidden in (str(self.root), self.relative, self.digest_name):
            self.assertNotIn(forbidden, out.getvalue())

    def test_cli_failure_hides_sensitive_source_and_manifest(self):
        self.digest.chmod(0o644)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main(["--source-root",str(self.source_root),
                           "--relative-file",self.relative,
                           "--digest-root",str(self.digest_root),
                           "--digest-file",self.digest_name])
        self.assertEqual(status, 2)
        self.assertEqual(out.getvalue(),"")
        for forbidden in (str(self.root),self.relative,self.digest_name):
            self.assertNotIn(forbidden,err.getvalue())

    def test_oversized_file_rejected_without_attempting_full_read(self):
        import tools.foj_stage295_owner_local_source_integrity as m
        with mock.patch.object(m, "MAX_SOURCE_BYTES", 64):
            self.assert_refused()

    def test_missing_digest_never_bootstraps_trust(self):
        self.digest.unlink()
        self.assert_refused()

    def test_double_pass_difference_fails(self):
        import tools.foj_stage295_owner_local_source_integrity as m
        real = m._pass
        count = [0]
        def second_modified(stream, size, *, save_prefix):
            count[0] += 1
            digest,prefix=real(stream,size,save_prefix=save_prefix)
            if count[0]==2:
                digest=bytes([digest[0]^1])+digest[1:]
            return digest,prefix
        with mock.patch.object(m, "_pass",side_effect=second_modified):
            self.assert_refused()

    def test_empty_source_refused(self):
        self.source.write_bytes(b"")
        self.seal(b"")
        self.assert_refused()


if __name__ == "__main__":
    unittest.main()
