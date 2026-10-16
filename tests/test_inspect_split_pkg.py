"""Read-only split ZIP tests built from generated data, not game files."""
import contextlib
import hashlib
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.inspect_pkg import PKGError
from tools.inspect_split_pkg import JoinedParts, inspect_split_archive, main


def synthetic_pkg() -> bytes:
    buf = bytearray(0x240)
    struct.pack_into(
        ">4sHHIIIIQQQ", buf, 0, b"\x7fPKG", 0x8000, 1,
        0xC0, 1, 12, 1, len(buf), 0x200, 0x40,
    )
    cid = b"EP0000-NPEB00148_00-TESTCONTENT000000"
    buf[0x30:0x30 + len(cid)] = cid
    struct.pack_into(">II4s", buf, 0xC0, 6, 4, b"ABCD")
    return bytes(buf)


class SplitArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def create_parts(self, members=None, *, compression=zipfile.ZIP_DEFLATED):
        if members is None:
            members = {"game/NPEB00148.pkg": synthetic_pkg()}
        archive_buffer = io.BytesIO()
        with zipfile.ZipFile(archive_buffer, "w", compression=compression) as zf:
            for name, data in members.items():
                zf.writestr(name, data)
        data = archive_buffer.getvalue()
        cut1 = max(1, len(data) // 3)
        cut2 = max(cut1 + 1, 2 * len(data) // 3)
        parts = []
        for index, payload in enumerate((data[:cut1], data[cut1:cut2], data[cut2:])):
            part = self.dir / f"fixture.zip.{index + 1:03d}"
            part.write_bytes(payload)
            parts.append(part)
        return parts

    def test_seekable_virtual_reader(self):
        paths = self.create_parts()
        original = b"".join(path.read_bytes() for path in paths)
        with JoinedParts(paths) as reader:
            self.assertEqual(reader.size, len(original))
            self.assertEqual(reader.read(13), original[:13])
            reader.seek(-15, io.SEEK_END)
            self.assertEqual(reader.read(), original[-15:])
            reader.seek(0)
            self.assertEqual(reader.read(), original)

    def test_pkg_header_without_extracting(self):
        parts = self.create_parts()
        result = inspect_split_archive(parts, expected_title_id="NPEB00148")
        self.assertEqual(result["archive"]["part_count"], 3)
        self.assertEqual(result["pkg"]["header"]["platform"], "PS3")
        self.assertEqual(result["pkg"]["metadata"][0]["title_id"], "ABCD")
        self.assertTrue(result["pkg"]["checks"]["declared_size_matches_file"])
        self.assertTrue(result["pkg"]["checks"]["expected_title_id_in_content_id"])
        self.assertFalse(result["archive"]["pkg_member_crc_verified"])

    def test_hash_and_crc(self):
        parts = self.create_parts()
        result = inspect_split_archive(parts, hash_pkg=True, verify_crc=True)
        self.assertEqual(result["pkg"]["sha256"], hashlib.sha256(synthetic_pkg()).hexdigest())
        self.assertTrue(result["archive"]["pkg_member_crc_verified"])
        self.assertTrue(result["archive"]["all_entries_crc_verified"])

    def test_crc_rejects_modified_package(self):
        parts = self.create_parts(compression=zipfile.ZIP_STORED)
        data = bytearray(b"".join(part.read_bytes() for part in parts))
        offset = data.index(synthetic_pkg())
        data[offset + 0x1F0] ^= 1
        altered = self.dir / "altered.zip"
        altered.write_bytes(data)
        with self.assertRaises(PKGError):
            inspect_split_archive([altered], verify_crc=True)

    def test_missing_part(self):
        parts = self.create_parts()
        parts[1].unlink()
        with self.assertRaises(FileNotFoundError):
            inspect_split_archive(parts)

    def test_wrong_order(self):
        parts = self.create_parts()
        with self.assertRaises(PKGError):
            inspect_split_archive(parts[::-1])

    def test_no_package(self):
        parts = self.create_parts({"readme.txt": b"hello"})
        with self.assertRaisesRegex(PKGError, "No matching"):
            inspect_split_archive(parts)

    def test_requires_member_for_multiple_pkgs(self):
        parts = self.create_parts({"a.pkg": synthetic_pkg(), "b.pkg": synthetic_pkg()})
        with self.assertRaisesRegex(PKGError, "More than one"):
            inspect_split_archive(parts)
        result = inspect_split_archive(parts, member="b.pkg")
        self.assertEqual(result["archive"]["pkg_member"], "b.pkg")

    def test_cli_json(self):
        parts = self.create_parts()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([*(str(p) for p in parts), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["pkg"]["header"]["pkg_type"], 1)


if __name__ == "__main__":
    unittest.main()
