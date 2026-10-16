"""Synthetic end-to-end tests for the PS3 debug-PKG / PSARC inspector.

No commercial game files or original PS3 keys are used in CI.
"""
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
import zlib

from tools.inspect_debug_pkg_assets import (
    DebugPKG, FormatError, PSARC, summarize, xor_debug_data,
)
from tools.inspect_split_pkg import JoinedParts


def synthetic_psarc(with_map=False):
    filenames = ["data/example.tga", "data/example.lua"]
    blobs = [("\n".join(filenames) + "\n").encode(), b"DDS " + b"X" * 40,
             b"-- synthetic Lua test\nvalue=1\n"]
    if with_map:
        filenames += [
            "data/maps/map1-1.coll",
            "data/maps/map1-1.vis",
            "data/maps/map1-1.ini",
        ]
        blobs[0] = ("\n".join(filenames) + "\n").encode()
        coll = (
            b"2,2,-10,-10,10,10,\n"
            b"0,0,0,0,0,0,false,false,\n"
            b"1,0,1,1,1,1,true,false,\n"
            b"0,1,0,1,2,3,false,true,\n"
            b"1,1,2,2,2,2,false,false,\n"
        )
        vis = (b"0\n2\n4\n" +
               b"0,0,false,true\n1,0,false,true\n" +
               b"0,1,false,true\n1,1,false,true\n")
        ini = b"[tree0]\nbase=tree\nlocation=1,2,3\n"
        blobs.extend([coll, vis, ini])
    compressed = [zlib.compress(blob) for blob in blobs]
    block_size = 65536
    toc_len = 32 + len(blobs) * 30 + len(blobs) * 2
    out = bytearray(struct.pack(
        ">4sI4sIIIII", b"PSAR", 0x00010004, b"zlib",
        toc_len, 30, len(blobs), block_size, 1,
    ))
    offset = toc_len
    for i, (plain, packed) in enumerate(zip(blobs, compressed)):
        out.extend(b"\x00" * 16)
        out.extend(i.to_bytes(4, "big"))
        out.extend(len(plain).to_bytes(5, "big"))
        out.extend(offset.to_bytes(5, "big"))
        offset += len(packed)
    for packed in compressed:
        out.extend(struct.pack(">H", len(packed)))
    for packed in compressed:
        out.extend(packed)
    assert len(out) == offset
    return bytes(out)


def synthetic_pkg(*, revision=0, with_map=False):
    psarc = synthetic_psarc(with_map=with_map)
    names = [b"PARAM.SFO", b"USRDIR/cdata.psarc"]
    body_start = 2 * 32 + sum(len(x) for x in names)
    body_start = (body_start + 15) & ~15
    data = bytearray(body_start)
    data[64:64 + len(names[0])] = names[0]
    data[64 + len(names[0]):64 + sum(len(x) for x in names)] = names[1]
    file0 = b"\x00PSF" + b"Y" * 16
    payloads = [file0, psarc]
    for i, (name, contents) in enumerate(zip(names, payloads)):
        data_off = len(data)
        data.extend(contents)
        filename_off = 64 + sum(len(x) for x in names[:i])
        struct.pack_into(">IIQQII", data, i * 32,
                         filename_off, len(name), data_off,
                         len(contents), 0x80000003, 0)
    header = bytearray(0x180)
    struct.pack_into(">4sHHIIIIQQQ", header, 0, b"\x7fPKG", revision,
                     1, 0xC0, 0, 0, len(names), len(header) + len(data),
                     len(header), len(data))
    digest = bytes(range(16))
    header[0x60:0x70] = digest
    return bytes(header) + xor_debug_data(digest, 0, bytes(data))


def make_parts(directory, data):
    zfile = io.BytesIO()
    with zipfile.ZipFile(zfile, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("test.pkg", data)
    content = zfile.getvalue()
    split = len(content) // 2 + 3
    paths = [Path(directory) / f"test.zip.{i:03d}" for i in (1, 2)]
    for part, chunk in zip(paths, (content[:split], content[split:])):
        part.write_bytes(chunk)
    return paths


class DebugPKGResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_random_access_stream(self):
        plain = b"0123456789abcdef" * 8
        digest = bytes(range(16))
        cipher = xor_debug_data(digest, 0, plain)
        self.assertNotEqual(cipher, plain)
        self.assertEqual(xor_debug_data(digest, 0, cipher), plain)
        self.assertEqual(xor_debug_data(digest, 19, cipher[19:77]), plain[19:77])
        self.assertEqual(xor_debug_data(digest, 1, cipher[1:2]), plain[1:2])

    def test_read_split_pkg_and_psarc_manifest(self):
        paths = make_parts(self.temp.name, synthetic_pkg())
        report = summarize([str(path) for path in paths])
        self.assertEqual(report["pkg_item_count"], 2)
        self.assertEqual(report["psarc"]["toc_entries"], 3)
        self.assertEqual(report["psarc"]["manifest_paths"], 2)
        self.assertEqual(report["psarc"]["extension_counts"], {
            ".lua": 1, ".tga": 1,
        })
        self.assertEqual(report["psarc"]["example_signatures"][".tga"],
                         "DDS_TEXTURE")
        self.assertEqual(report["psarc"]["example_signatures"][".lua"],
                         "unknown")
        self.assertEqual(len(report["pkg_items"]), 2)
        self.assertNotIn("-- synthetic Lua test", json.dumps(report))
        self.assertNotIn("DDS X", json.dumps(report))

    def test_inline_original_style_map_summary(self):
        paths = make_parts(self.temp.name, synthetic_pkg(with_map=True))
        report = summarize([str(path) for path in paths], map_name="map1-1")
        selected = report["selected_map"]
        self.assertEqual(selected["collision"]["width"], 2)
        self.assertEqual(selected["collision"]["cells"], 4)
        self.assertEqual(selected["collision"]["flag_true_counts"], [1, 1])
        self.assertEqual(selected["visibility"]["records"], 4)
        self.assertEqual(selected["placements"]["section_count"], 1)
        self.assertNotIn("base=tree", json.dumps(report))

    def test_explicit_export_only_one_local_coll_and_never_overwrites(self):
        from tools.export_local_coll import local_export
        from tools.inspect_map_coll import MapFormatError
        parts = make_parts(self.temp.name, synthetic_pkg(with_map=True))
        dest = Path(self.temp.name) / "map1-1.coll"
        self.assertFalse(dest.exists())
        report = local_export(parts, "map1-1", dest)
        self.assertEqual(report["grid_width"], 2)
        self.assertEqual(report["grid_height"], 2)
        self.assertEqual(report["bytes_written"], len(dest.read_bytes()))
        self.assertEqual(dest.read_bytes()[:6], b"2,2,-1")
        with self.assertRaises(FileExistsError):
            local_export(parts, "map1-1", dest)
        with self.assertRaises(MapFormatError):
            local_export(parts, "../wrong", Path(self.temp.name) / "wrong.coll")
        self.assertEqual(len(list(Path(self.temp.name).glob("*.coll"))), 1)

    def test_wrong_revision_fails_without_fallback(self):
        paths = make_parts(self.temp.name, synthetic_pkg(revision=0x8000))
        with self.assertRaisesRegex(FormatError, "non-finalized"):
            summarize([str(path) for path in paths])

    def test_bad_debug_payload_fails_closed(self):
        pkg = bytearray(synthetic_pkg())
        pkg[0x180] ^= 0x40
        paths = make_parts(self.temp.name, bytes(pkg))
        with self.assertRaises(FormatError):
            summarize([str(path) for path in paths])

    def test_missing_or_wrong_input_zip(self):
        with self.assertRaises(FileNotFoundError):
            summarize([str(Path(self.temp.name) / "missing.zip.001")])

    def test_pkg_bounds_reject_invalid_requests(self):
        paths = make_parts(self.temp.name, synthetic_pkg())
        from tools.inspect_debug_pkg_assets import unpack_stored_zip
        with JoinedParts(paths) as joined:
            begin, length = unpack_stored_zip(joined)
            pkg = DebugPKG(joined, begin, length)
            with self.assertRaises(FormatError):
                pkg.read(-1, 5)
            with self.assertRaises(FormatError):
                pkg.read(pkg.data_size, 1)
            self.assertEqual(pkg.items()[1]["path"], "USRDIR/cdata.psarc")

    def test_psarc_rejects_malformed_toc(self):
        paths = make_parts(self.temp.name, synthetic_pkg())
        from tools.inspect_debug_pkg_assets import unpack_stored_zip
        with JoinedParts(paths) as joined:
            begin, length = unpack_stored_zip(joined)
            pkg = DebugPKG(joined, begin, length)
            psarc_item = pkg.items()[1]
            psarc = PSARC(pkg, psarc_item["offset"], psarc_item["size"])
            self.assertEqual(psarc.entry_data(0).decode(),
                             "data/example.tga\ndata/example.lua\n")
            self.assertEqual(psarc.entry_data(1)[:4], b"DDS ")


if __name__ == "__main__":
    unittest.main()
