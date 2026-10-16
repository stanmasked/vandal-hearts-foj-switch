"""Tests only use synthetic header bytes, never retail game data."""
import contextlib
import hashlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.inspect_pkg import PKGError, inspect_pkg, main


def make_pkg(
    path: Path,
    *,
    magic: bytes = b"\x7fPKG",
    revision: int = 0x8000,
    pkg_type: int = 1,
    declared_size: int = 0x240,
    metadata_size: int = 12,
    metadata_count: int = 1,
    content_id: bytes = b"EP0000-NPEB00148_00-TESTCONTENT000000",
) -> None:
    buf = bytearray(0x240)
    struct.pack_into(
        ">4sHHIIIIQQQ",
        buf, 0, magic, revision, pkg_type,
        0xC0, metadata_count, metadata_size, 1,
        declared_size, 0x200, 0x40,
    )
    buf[0x30:0x30 + len(content_id)] = content_id
    # One synthetic metadata record (type 6, payload 4 bytes).
    struct.pack_into(">III", buf, 0xC0, 6, 4, 0x01020304)
    path.write_bytes(buf)


class InspectPKGTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "synthetic.pkg"

    def test_valid_ps3_retail_pkg(self):
        make_pkg(self.path)
        r = inspect_pkg(self.path, expected_title_id="NPEB00148")
        self.assertEqual(r["header"]["platform"], "PS3")
        self.assertEqual(r["header"]["revision_kind"], "retail")
        self.assertEqual(r["metadata"], [{"id": 6, "size": 4}])
        self.assertTrue(r["checks"]["declared_size_matches_file"])
        self.assertTrue(r["checks"]["data_region_within_file"])
        self.assertTrue(r["checks"]["expected_title_id_in_content_id"])
        self.assertEqual(r["warnings"], [])

    def test_nonfinalized_ps3_header_with_typed_metadata(self):
        # Generated structure uses the public PKG schema, not game bytes.
        make_pkg(self.path, revision=0, metadata_count=5, metadata_size=64)
        data = bytearray(self.path.read_bytes())
        payloads = [
            (1, struct.pack(">I", 3)),
            (2, struct.pack(">I", 5)),
            (3, struct.pack(">I", 78)),
            (4, struct.pack(">Q", 0x40)),
            (5, bytes.fromhex("17320100")),
        ]
        off = 0xC0
        for kind, body in payloads:
            struct.pack_into(">II", data, off, kind, len(body))
            data[off + 8:off + 8 + len(body)] = body
            off += 8 + len(body)
        self.assertEqual(off, 0xC0 + 64)
        self.path.write_bytes(data)

        r = inspect_pkg(self.path, expected_title_id="NPEB00148")
        self.assertEqual(r["header"]["revision_kind"], "debug")
        self.assertEqual(r["header"]["trailer_size"], 0)
        self.assertEqual(r["metadata"][0]["drm_type"], 3)
        self.assertEqual(r["metadata"][1]["content_type"], 5)
        self.assertEqual(r["metadata"][2]["package_flags"], 78)
        self.assertEqual(r["metadata"][3]["metadata_package_size"], 64)
        self.assertEqual(r["metadata"][4]["builder_version_raw"], "17320100")
        self.assertEqual(r["warnings"], [])

    def test_rejects_wrong_magic(self):
        make_pkg(self.path, magic=b"XXXX")
        with self.assertRaisesRegex(PKGError, "Invalid PKG magic"):
            inspect_pkg(self.path)

    def test_rejects_zip_input_with_helpful_error(self):
        make_pkg(self.path, magic=b"PK\x03\x04")
        with self.assertRaisesRegex(PKGError, "ZIP archive"):
            inspect_pkg(self.path)

    def test_rejects_truncated_header(self):
        self.path.write_bytes(b"\x7fPKG")
        with self.assertRaisesRegex(PKGError, "too small"):
            inspect_pkg(self.path)

    def test_warns_on_size_mismatch(self):
        make_pkg(self.path, declared_size=0x230)
        r = inspect_pkg(self.path)
        self.assertFalse(r["checks"]["declared_size_matches_file"])
        self.assertIn("Declared PKG size differs from actual file size", r["warnings"])

    def test_warns_on_incomplete_metadata_record(self):
        make_pkg(self.path, metadata_size=8)
        r = inspect_pkg(self.path)
        self.assertEqual(r["metadata"], [])
        self.assertTrue(any("payload extends" in w for w in r["warnings"]))

    def test_wrong_title_id_is_reported(self):
        make_pkg(self.path)
        r = inspect_pkg(self.path, expected_title_id="NPUB00000")
        self.assertFalse(r["checks"]["expected_title_id_in_content_id"])

    def test_streamed_hash(self):
        make_pkg(self.path)
        r = inspect_pkg(self.path, hash_file=True)
        self.assertEqual(r["sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_json_cli(self):
        make_pkg(self.path)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([str(self.path), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["header"]["pkg_type"], 1)


if __name__ == "__main__":
    unittest.main()
