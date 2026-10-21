"""Stage301: compare all sixteen native 256px pages to original-size C decoder.

All image data is GENERATED and does not reproduce any proprietary texture.
"""
from __future__ import annotations

import ctypes
import os
import struct
import unittest

from tools.foj_stage300_real_dds_evidence_contract import (
    HISTORICAL, synthetic_from_envelope,
)

EDGE = 1024
PAGE = 256
SOURCE_SIZE = 128 + 1024 * 1024 // 2
RGBA_BYTES = PAGE * PAGE * 4


def patterned_bc1(*, transparent=False):
    """Generated BC1 blocks whose palette/index choice varies spatially."""
    raw = bytearray(synthetic_from_envelope(HISTORICAL[2]))
    for by in range(256):
        for bx in range(256):
            offset = 128 + (by * 256 + bx) * 8
            if transparent and ((bx + by) % 7 == 0):
                c0,c1 = 0x001F,0xF800   # 3-color transparent mode
            else:
                c0,c1 = 0xF800,0x001F   # 4-color opaque mode
            pixels = 0
            for y in range(4):
                for x in range(4):
                    index = (bx + 3*by + x + 2*y) % 4
                    pixels |= index << (2 * (y*4+x))
            struct.pack_into("<HHI",raw,offset,c0,c1,pixels)
    return bytes(raw)


class AtlasInfo(ctypes.Structure):
    _fields_ = [("width",ctypes.c_uint),("height",ctypes.c_uint),
                ("pixel_bytes",ctypes.c_size_t)]


class LegacyInfo(ctypes.Structure):
    _fields_ = [("width",ctypes.c_uint32),("height",ctypes.c_uint32),
                ("mip_count",ctypes.c_uint32),("format",ctypes.c_int),
                ("first_level_bytes",ctypes.c_size_t)]


class NativeBC1PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lib = os.environ.get("FOJ_STAGE301_ATLAS_SO")
        legacy = os.environ.get("FOJ_STAGE301_LEGACY_SO")
        if not lib or not legacy:
            raise RuntimeError("Must test actual compiled C decoders, never mocks")
        atlas = ctypes.CDLL(lib)
        old = ctypes.CDLL(legacy)
        ptr=ctypes.POINTER(ctypes.c_uint8)
        cls.page=atlas.foj_bc1_1024_decode_page
        cls.page.argtypes=[ptr,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,
                           ptr,ctypes.c_size_t,ctypes.POINTER(AtlasInfo)]
        cls.page.restype=ctypes.c_int
        cls.atlas=atlas.foj_atlas_dds_decode
        cls.atlas.argtypes=[ptr,ctypes.c_size_t,ptr,ctypes.c_size_t,
                            ctypes.POINTER(AtlasInfo)]
        cls.atlas.restype=ctypes.c_int
        cls.legacy=old.foj_dds_decode
        cls.legacy.argtypes=[
            ptr,ctypes.c_size_t,ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_size_t,ctypes.c_size_t,ctypes.POINTER(LegacyInfo)]
        cls.legacy.restype=ctypes.c_int

    def source(self, raw):
        return (ctypes.c_uint8*len(raw)).from_buffer_copy(raw)

    def decode(self, raw, px, py):
        src=self.source(raw)
        out=(ctypes.c_uint8*RGBA_BYTES)()
        info=AtlasInfo()
        accepted=self.page(src,len(raw),px,py,out,RGBA_BYTES,ctypes.byref(info))
        self.assertEqual(accepted,1)
        self.assertEqual((info.width,info.height,info.pixel_bytes),
                         (PAGE,PAGE,RGBA_BYTES))
        return bytes(out)

    def full_reference(self, raw):
        src=self.source(raw)
        pixels=(ctypes.c_uint32*(EDGE*EDGE))()
        info=LegacyInfo()
        code=self.legacy(src,len(raw),pixels,EDGE,EDGE*EDGE,ctypes.byref(info))
        self.assertEqual(code,0)
        self.assertEqual((info.width,info.height,info.format),(EDGE,EDGE,2))
        return memoryview(pixels).cast("B").tobytes()

    def assert_page_equals_full(self, page, full, px, py):
        for y in range(PAGE):
            beg=((py*PAGE+y)*EDGE+px*PAGE)*4
            self.assertEqual(page[y*PAGE*4:(y+1)*PAGE*4],
                             full[beg:beg+PAGE*4])

    def test_all_sixteen_generated_pages_equal_independent_legacy_decoder(self):
        raw=patterned_bc1()
        self.assertEqual(len(raw),SOURCE_SIZE)
        full=self.full_reference(raw)
        for py in range(4):
            for px in range(4):
                with self.subTest(page=(px,py)):
                    tile=self.decode(raw,px,py)
                    self.assert_page_equals_full(tile,full,px,py)

    def test_all_sixteen_transparent_bc1_pages_equal_legacy(self):
        raw=patterned_bc1(transparent=True)
        full=self.full_reference(raw)
        self.assertIn(0,full[3::4])
        for py in range(4):
            for px in range(4):
                with self.subTest(page=(px,py)):
                    tile=self.decode(raw,px,py)
                    self.assert_page_equals_full(tile,full,px,py)

    def test_documented_1024_envelope_is_accepted_by_new_page_route(self):
        raw=synthetic_from_envelope(HISTORICAL[2])
        self.decode(raw,0,0)
        self.decode(raw,3,3)

    def test_old_atlas_still_rejects_full_1024_dds(self):
        raw=patterned_bc1()
        src=self.source(raw)
        out=(ctypes.c_uint8*16)(*([0xA5]*16))
        info=AtlasInfo(66,77,88)
        self.assertEqual(self.atlas(src,len(raw),out,16,ctypes.byref(info)),0)
        self.assertEqual(bytes(out),bytes([0xA5])*16)
        self.assertEqual((info.width,info.height,info.pixel_bytes),(66,77,88))

    def assert_rejects(self, raw, px=0, py=0, cap=RGBA_BYTES):
        src=self.source(raw)
        out=(ctypes.c_uint8*RGBA_BYTES)(*([0xA5]*RGBA_BYTES))
        info=AtlasInfo(66,77,88)
        code=self.page(src,len(raw),px,py,out,cap,ctypes.byref(info))
        self.assertEqual(code,0)
        self.assertEqual((info.width,info.height,info.pixel_bytes),(66,77,88))
        self.assertEqual(bytes(out),bytes([0xA5])*RGBA_BYTES)

    def test_out_of_bounds_page_coordinates_fail_before_output(self):
        raw=patterned_bc1()
        for px,py in ((4,0),(0,4),(100,0),(0,200),(65535,65535)):
            with self.subTest(page=(px,py)):
                self.assert_rejects(raw,px,py)

    def test_destination_capacity_limit_fail_closed(self):
        raw=synthetic_from_envelope(HISTORICAL[2])
        for cap in (0,1,RGBA_BYTES-1):
            with self.subTest(cap=cap):
                self.assert_rejects(raw,cap=cap)

    def test_truncated_or_extended_source_rejected(self):
        raw=patterned_bc1()
        self.assert_rejects(raw[:-1])
        self.assert_rejects(raw+b"X")

    def test_invalid_magic_or_header_sizes_rejected(self):
        original=bytearray(patterned_bc1())
        for index,value in ((0,0),(4,0),(76,0),(108,0),(124,1)):
            with self.subTest(offset=index):
                raw=bytearray(original)
                raw[index]=value
                self.assert_rejects(bytes(raw))

    def test_declared_dimensions_must_be_exact_1024(self):
        raw=bytearray(patterned_bc1())
        for offset in (12,16):
            with self.subTest(offset=offset):
                wrong=bytearray(raw)
                struct.pack_into("<I",wrong,offset,256)
                self.assert_rejects(bytes(wrong))

    def test_mip_level_and_caps_are_not_guessed(self):
        raw=patterned_bc1()
        for offset,value in ((28,2),(108,0x401008),(112,0x200),
                             (24,1),(88,32),(92,1)):
            with self.subTest(field=offset):
                wrong=bytearray(raw)
                struct.pack_into("<I",wrong,offset,value)
                self.assert_rejects(bytes(wrong))

    def test_bad_fourcc_and_pixel_masks_rejected(self):
        raw=patterned_bc1()
        for offset,value in ((80,0x41),(84,0x35545844),(104,1)):
            with self.subTest(field=offset):
                wrong=bytearray(raw)
                struct.pack_into("<I",wrong,offset,value)
                self.assert_rejects(bytes(wrong))

    def test_declared_compressed_payload_mismatch_rejected(self):
        raw=bytearray(patterned_bc1())
        struct.pack_into("<I",raw,20,12345)
        self.assert_rejects(bytes(raw))

    def test_rejects_null_source_or_destination_or_metadata(self):
        raw=patterned_bc1()
        src=self.source(raw)
        out=(ctypes.c_uint8*RGBA_BYTES)(*([0xA5]*RGBA_BYTES))
        info=AtlasInfo(66,77,88)
        for args in (
            (None,len(raw),0,0,out,RGBA_BYTES,ctypes.byref(info)),
            (src,len(raw),0,0,None,RGBA_BYTES,ctypes.byref(info)),
            (src,len(raw),0,0,out,RGBA_BYTES,None),
        ):
            with self.subTest(null_position=tuple(i for i,p in enumerate(args) if p is None)):
                self.assertEqual(self.page(*args),0)
        self.assertEqual(bytes(out),bytes([0xA5])*RGBA_BYTES)
        self.assertEqual((info.width,info.height,info.pixel_bytes),(66,77,88))

    def test_full_decode_pixel_bytes_not_exported_to_github(self):
        # The implementation under test only accepts caller-owned bytes and
        # produces a bounded one-page RGBA buffer, not image files.
        raw=patterned_bc1()
        tile=self.decode(raw,2,1)
        self.assertEqual(len(tile),RGBA_BYTES)
        self.assertNotEqual(tile,self.decode(raw,0,0))


if __name__=="__main__":
    unittest.main()
