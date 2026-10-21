"""Stage300: actual two-C-decoder parity on synthetic DDS with documented sizes."""
from __future__ import annotations

import ctypes
from pathlib import Path
import struct
import unittest

from tools.foj_gpu_local_dds_preflight import (
    MAX_WIDTH, classify_classic_dds,
)
from tools.foj_stage300_real_dds_evidence_contract import (
    HISTORICAL, DocumentedEnvelope, classify_reconciliation,
    synthetic_from_envelope,
)


class EvidenceMetadataTests(unittest.TestCase):
    def test_historical_source_report_exists_in_repo(self):
        text = Path("docs/REAL_RESOURCE_SIGNATURES.md").read_text()
        self.assertIn("2026-10-16", text)
        self.assertIn("five", text.lower())
        self.assertIn("DDS", text)
        self.assertIn("Pillow", text)

    def test_five_existing_documented_profiles_only(self):
        self.assertEqual(len(HISTORICAL), 5)
        self.assertEqual([e.format for e in HISTORICAL].count("BGRA8"), 2)
        self.assertEqual([e.format for e in HISTORICAL].count("BC1/DXT1"), 3)
        self.assertEqual([e.width for e in HISTORICAL].count(1024), 1)
        self.assertEqual([e.width for e in HISTORICAL].count(256), 4)

    def test_generated_headers_and_lengths_match_published_metadata(self):
        for e in HISTORICAL:
            with self.subTest(asset=e.name):
                data=synthetic_from_envelope(e)
                self.assertEqual(data[:4],b"DDS ")
                self.assertEqual(len(data),e.bytes)
                self.assertEqual(struct.unpack_from("<II",data,12),(e.height,e.width))
                self.assertEqual(struct.unpack_from("<I",data,28)[0],1)

    def test_legacy_file_extension_is_not_image_format(self):
        self.assertTrue(all(e.name.endswith(".tga") for e in HISTORICAL))
        self.assertTrue(all(synthetic_from_envelope(e).startswith(b"DDS ")
                            for e in HISTORICAL))

    def test_no_unverified_source_header_claim(self):
        result=classify_reconciliation()
        self.assertFalse(result["real_source_bytes_reexamined_in_stage300"])
        self.assertFalse(result["actual_source_headers_accepted_by_native_gpu_proven"])
        self.assertFalse(result["native_texture_gpu_rendering_of_original_foj_content_proven"])
        self.assertEqual(result["native_atlas_dimension_format_envelope_eligible"],4)
        self.assertEqual(result["native_atlas_dimension_format_envelope_blocked"],1)

    def test_the_1024_bc1_atlas_is_not_directly_compatible(self):
        e=next(x for x in HISTORICAL if x.width==1024)
        self.assertEqual(e.format,"BC1/DXT1")
        self.assertGreater(e.width,MAX_WIDTH)
        with self.assertRaises(ValueError):
            classify_classic_dds(synthetic_from_envelope(e))

    def test_other_four_synthetic_profiles_are_native_eligible(self):
        for e in HISTORICAL:
            if e.width>MAX_WIDTH:
                continue
            with self.subTest(asset=e.name):
                result=classify_classic_dds(synthetic_from_envelope(e))
                self.assertEqual((result["format"],result["width"],result["height"]),
                                 (e.format,e.width,e.height))

    def test_payload_sizes_are_exact_base_level_only(self):
        for e in HISTORICAL:
            expected=128+(e.width*e.height*4 if e.format=="BGRA8" else
                          ((e.width+3)//4)*((e.height+3)//4)*8)
            self.assertEqual(e.bytes,expected)
            self.assertEqual(len(synthetic_from_envelope(e)),expected)

    def test_synthetic_over_and_under_size_not_silent(self):
        e=HISTORICAL[0]
        for wrong in (e.bytes-1,e.bytes+1):
            with self.subTest(size=wrong), self.assertRaises(ValueError):
                synthetic_from_envelope(DocumentedEnvelope(
                    e.name,e.width,e.height,e.format,wrong))

    def test_unsupported_envelope_rejected(self):
        for e in (
            DocumentedEnvelope("fake.tga",8,8,"BC3",144),
            DocumentedEnvelope("fake.tga",4097,8,"BGRA8",0),
            DocumentedEnvelope("fake.tga",15,16,"BC1/DXT1",0),
        ):
            with self.subTest(format=e.format),self.assertRaises(ValueError):
                synthetic_from_envelope(e)

    def test_reconciliation_lists_all_and_no_new_asset_hashes(self):
        import json
        receipt=classify_reconciliation()
        self.assertEqual({x["documented_name"] for x in receipt["source_files"]},
                         {x.name for x in HISTORICAL})
        text=json.dumps(receipt)
        self.assertNotIn("sha256",text)
        self.assertNotIn("private_root",text)


class NativeHistoricalDDSParity(unittest.TestCase):
    class LegacyInfo(ctypes.Structure):
        _fields_ = [
            ("width",ctypes.c_uint32),("height",ctypes.c_uint32),
            ("mip_count",ctypes.c_uint32),("format",ctypes.c_int),
            ("first_level_bytes",ctypes.c_size_t),
        ]

    class AtlasInfo(ctypes.Structure):
        _fields_ = [
            ("width",ctypes.c_uint),("height",ctypes.c_uint),
            ("pixel_bytes",ctypes.c_size_t),
        ]

    @classmethod
    def setUpClass(cls):
        import os
        legacy=os.environ.get("FOJ_STAGE300_LEGACY_SO")
        atlas=os.environ.get("FOJ_STAGE300_ATLAS_SO")
        if not legacy or not atlas:
            raise RuntimeError("Stage300 requires both real compiled C DDS decoders")
        cls.legacy=ctypes.CDLL(legacy)
        cls.atlas=ctypes.CDLL(atlas)
        ptr=ctypes.POINTER(ctypes.c_uint8)
        cls.legacy_decode=cls.legacy.foj_dds_decode
        cls.legacy_decode.argtypes=[
            ptr,ctypes.c_size_t,ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_size_t,ctypes.c_size_t,
            ctypes.POINTER(cls.LegacyInfo)]
        cls.legacy_decode.restype=ctypes.c_int
        cls.atlas_decode=cls.atlas.foj_atlas_dds_decode
        cls.atlas_decode.argtypes=[
            ptr,ctypes.c_size_t,ptr,ctypes.c_size_t,
            ctypes.POINTER(cls.AtlasInfo)]
        cls.atlas_decode.restype=ctypes.c_int

    def run_legacy(self, blob, e):
        buf=(ctypes.c_uint8*len(blob)).from_buffer_copy(blob)
        n=e.width*e.height
        dest=(ctypes.c_uint32*n)()
        info=self.LegacyInfo()
        self.assertEqual(
            self.legacy_decode(buf,len(blob),dest,e.width,n,ctypes.byref(info)),0)
        self.assertEqual((info.width,info.height),(e.width,e.height))
        self.assertEqual(info.mip_count,1)
        self.assertEqual(info.format,1 if e.format=="BGRA8" else 2)
        return bytes(dest)

    def run_atlas(self, blob, e):
        buf=(ctypes.c_uint8*len(blob)).from_buffer_copy(blob)
        n=e.width*e.height*4
        dest=(ctypes.c_uint8*n)()
        info=self.AtlasInfo()
        value=self.atlas_decode(buf,len(blob),dest,n,ctypes.byref(info))
        self.assertEqual(value,1)
        self.assertEqual((info.width,info.height,info.pixel_bytes),
                         (e.width,e.height,n))
        return bytes(dest)

    def test_historical_256_synthetic_samples_agree_across_two_real_c_decoders(self):
        for e in HISTORICAL:
            if e.width>MAX_WIDTH:
                continue
            with self.subTest(asset=e.name):
                blob=synthetic_from_envelope(e)
                self.assertEqual(self.run_legacy(blob,e),self.run_atlas(blob,e))

    def test_historical_1024_synthetic_bc1_supported_by_legacy_not_gpu_atlas(self):
        e=HISTORICAL[2]
        blob=synthetic_from_envelope(e)
        self.assertEqual(len(self.run_legacy(blob,e)),1024*1024*4)
        ptr=(ctypes.c_uint8*len(blob)).from_buffer_copy(blob)
        untouched=(ctypes.c_uint8*16)(*([0x5a]*16))
        info=self.AtlasInfo(123,456,789)
        self.assertEqual(self.atlas_decode(ptr,len(blob),untouched,16,
                                           ctypes.byref(info)),0)
        self.assertEqual(bytes(untouched),bytes([0x5a])*16)
        self.assertEqual((info.width,info.height,info.pixel_bytes),(123,456,789))

    def test_wrong_256_dds_source_mask_rejected_by_native_atlas(self):
        e=HISTORICAL[0]
        blob=bytearray(synthetic_from_envelope(e))
        struct.pack_into("<I",blob,92,0x12345678)
        src=(ctypes.c_uint8*len(blob)).from_buffer_copy(blob)
        sentinel=(ctypes.c_uint8*16)(*([0x33]*16))
        info=self.AtlasInfo(1,2,3)
        self.assertEqual(self.atlas_decode(src,len(blob),sentinel,16,
                                           ctypes.byref(info)),0)
        self.assertEqual(bytes(sentinel),bytes([0x33])*16)
        self.assertEqual((info.width,info.height,info.pixel_bytes),(1,2,3))

    def test_bc1_transparent_palette_mode_agrees_across_c_decoders(self):
        e=HISTORICAL[3]
        blob=bytearray(synthetic_from_envelope(e))
        struct.pack_into("<HHI",blob,128,0x001f,0xf800,0xffffffff)
        self.assertEqual(self.run_legacy(bytes(blob),e),
                         self.run_atlas(bytes(blob),e))


if __name__=="__main__":
    unittest.main()
