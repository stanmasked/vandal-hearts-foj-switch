"""Stage303: real C nearest UV mapper + generated full-BC1 pixel parity.

Only invented BC1 pixels. Real GPU UV seam behavior not claimed.
"""
from __future__ import annotations

import ctypes
import math
import os
import struct
import unittest

from tools.foj_stage300_real_dds_evidence_contract import HISTORICAL, synthetic_from_envelope

EDGE=1024
PAGE=256
DDSLEN=128+1024*1024//2
UV_CENTERS=(0,1,2,127,254,255,256,257,383,510,511,512,513,
            639,766,767,768,769,895,1021,1022,1023)
SEAMS=(0,256,512,768,1023)


class PageUv(ctypes.Structure):
    _fields_=[
        ("atlas_x",ctypes.c_uint32),
        ("atlas_y",ctypes.c_uint32),
        ("page_x",ctypes.c_uint32),
        ("page_y",ctypes.c_uint32),
        ("local_x",ctypes.c_uint32),
        ("local_y",ctypes.c_uint32),
        ("local_u",ctypes.c_float),
        ("local_v",ctypes.c_float),
    ]


class AtlasInfo(ctypes.Structure):
    _fields_=[("width",ctypes.c_uint32),("height",ctypes.c_uint32),
              ("mip_count",ctypes.c_uint32),("format",ctypes.c_int),
              ("first_level_bytes",ctypes.c_size_t)]


class PixelInfo(ctypes.Structure):
    _fields_=[("width",ctypes.c_uint),("height",ctypes.c_uint),
              ("pixel_bytes",ctypes.c_size_t)]


def invented_bc1():
    image=bytearray(synthetic_from_envelope(HISTORICAL[2]))
    assert len(image)==DDSLEN
    for row in range(256):
        for col in range(256):
            px,py=col//64,row//64
            # Different indexed 565 palette on every page; channel
            # transparency varies with BC1 palette endpoint ordering.
            c0=0xF800-((px*2+py)*0x200)  # nonuniform red primary
            c1=0x001f+(px*31+py*121)
            if (px+py)%3==0:
                c0,c1=c1,c0
            indices=0
            for by in range(4):
                for bx in range(4):
                    indices |= ((col+row+px+by+2*bx)&3) << (2*(by*4+bx))
            struct.pack_into("<HHI",image,128+(row*256+col)*8,
                             c0,c1,indices)
    return bytes(image)


def before32(f):
    return bytes(ctypes.string_at(ctypes.byref(f),ctypes.sizeof(f)))


def float_before(value):
    u=struct.unpack("<I",struct.pack("<f",value))[0]
    assert u>0
    return struct.unpack("<f",struct.pack("<I",u-1))[0]


def float_after(value):
    u=struct.unpack("<I",struct.pack("<f",value))[0]
    return struct.unpack("<f",struct.pack("<I",u+1))[0]


class NativeUVBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        so=os.environ.get("FOJ_STAGE303_PAGE_SO")
        legacy=os.environ.get("FOJ_STAGE303_LEGACY_SO")
        if not so or not legacy:
            raise RuntimeError("Stage303 must test compiled actual C code")
        page=ctypes.CDLL(so)
        old=ctypes.CDLL(legacy)
        cls.resolve=page.foj_bc1_1024_resolve_uv
        cls.resolve.argtypes=[ctypes.c_float,ctypes.c_float,
                             ctypes.POINTER(PageUv)]
        cls.resolve.restype=ctypes.c_int
        cls.resolve_int=page.foj_bc1_1024_resolve_texel
        cls.resolve_int.argtypes=[ctypes.c_uint,ctypes.c_uint,
                                 ctypes.POINTER(PageUv)]
        cls.resolve_int.restype=ctypes.c_int
        cls.decode_page=page.foj_bc1_1024_decode_page
        ptr=ctypes.POINTER(ctypes.c_uint8)
        cls.decode_page.argtypes=[ptr,ctypes.c_size_t,ctypes.c_uint,
                                 ctypes.c_uint,ptr,ctypes.c_size_t,
                                 ctypes.POINTER(PixelInfo)]
        cls.decode_page.restype=ctypes.c_int
        cls.full=old.foj_dds_decode
        cls.full.argtypes=[
            ptr,ctypes.c_size_t,ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_size_t,ctypes.c_size_t,ctypes.POINTER(AtlasInfo)]
        cls.full.restype=ctypes.c_int
        cls.source=invented_bc1()
        cls.source_c=(ctypes.c_uint8*len(cls.source)).from_buffer_copy(cls.source)
        legacy_out=(ctypes.c_uint32*(EDGE*EDGE))()
        legacy_info=AtlasInfo()
        assert cls.full(cls.source_c,len(cls.source),legacy_out,EDGE,
                        EDGE*EDGE,ctypes.byref(legacy_info))==0
        cls.whole=memoryview(legacy_out).cast("B").tobytes()

    @classmethod
    def tearDownClass(cls):
        cls.whole=b""
        cls.source=b""

    def resolve_x_y(self,x,y):
        result=PageUv()
        self.assertEqual(self.resolve_int(x,y,ctypes.byref(result)),1)
        return result

    def resolve_uv(self,u,v):
        result=PageUv()
        self.assertEqual(self.resolve(u,v,ctypes.byref(result)),1)
        return result

    def assert_coordinates(self,coords,x,y):
        self.assertEqual((coords.atlas_x,coords.atlas_y),(x,y))
        self.assertEqual((coords.page_x,coords.page_y),(x//PAGE,y//PAGE))
        self.assertEqual((coords.local_x,coords.local_y),(x%PAGE,y%PAGE))
        self.assertEqual(coords.local_u,((x%PAGE)+0.5)/PAGE)
        self.assertEqual(coords.local_v,((y%PAGE)+0.5)/PAGE)
        self.assertGreater(coords.local_u,0)
        self.assertLess(coords.local_u,1)
        self.assertGreater(coords.local_v,0)
        self.assertLess(coords.local_v,1)

    def test_integer_all_border_and_near_border_coordinates(self):
        for y in UV_CENTERS:
            for x in UV_CENTERS:
                with self.subTest(x=x,y=y):
                    self.assert_coordinates(self.resolve_x_y(x,y),x,y)

    def test_float_texel_centers_equal_integer_mapping_near_every_seam(self):
        for y in UV_CENTERS:
            for x in UV_CENTERS:
                with self.subTest(x=x,y=y):
                    uv=self.resolve_uv((x+0.5)/EDGE,(y+0.5)/EDGE)
                    self.assert_coordinates(uv,x,y)

    def test_all_atlas_x_on_eight_distinct_horizontal_rows(self):
        for y in (0,255,256,511,512,767,768,1023):
            for x in range(EDGE):
                coords=self.resolve_uv((x+0.5)/EDGE,(y+0.5)/EDGE)
                self.assertEqual((coords.atlas_x,coords.atlas_y),(x,y))
                self.assertEqual((coords.page_x,coords.page_y),(x//PAGE,y//PAGE))

    def test_exact_normalized_boundaries_select_right_or_lower_page(self):
        for index in (1,2,3):
            edge=index/4
            point=self.resolve_uv(edge,edge)
            self.assert_coordinates(point,index*256,index*256)

    def test_immediately_below_boundary_selects_left_or_upper(self):
        for index in (1,2,3):
            edge=index/4
            point=self.resolve_uv(float_before(edge),float_before(edge))
            self.assertEqual((point.page_x,point.page_y),(index-1,index-1))
            self.assertEqual((point.local_x,point.local_y),(255,255))

    def test_immediately_after_boundary_stays_on_right_lower(self):
        for index in (1,2,3):
            edge=index/4
            point=self.resolve_uv(float_after(edge),float_after(edge))
            self.assertEqual((point.page_x,point.page_y),(index,index))
            self.assertEqual((point.local_x,point.local_y),(0,0))

    def test_uv_one_is_final_pixel_not_wrap(self):
        self.assert_coordinates(self.resolve_uv(1.,1.),1023,1023)
        self.assert_coordinates(self.resolve_uv(1.,0.),1023,0)
        self.assert_coordinates(self.resolve_uv(0.,1.),0,1023)

    def test_uv_zero_and_negative_zero_select_origin(self):
        self.assert_coordinates(self.resolve_uv(-0.0,-0.0),0,0)
        self.assert_coordinates(self.resolve_uv(0.,0.),0,0)

    def test_out_of_range_finite_uv_preserves_output(self):
        for u,v in ((-0.1,0.5),(0.5,-0.1),(1.1,0.5),
                    (0.5,1.1),(-999.,0.),(999.,0.),
                    (float_after(1.),0.),(0.,float_after(1.))):
            with self.subTest(uv=(u,v)):
                output=PageUv(666,777,888,999,111,222,0.3,0.4)
                initial=before32(output)
                self.assertEqual(self.resolve(u,v,ctypes.byref(output)),0)
                self.assertEqual(before32(output),initial)

    def test_nan_infinite_uv_refused_without_mutation(self):
        for u,v in ((math.nan,0.),(0.,math.nan),(math.inf,0.),
                    (0.,-math.inf),(-math.inf,1.)):
            out=PageUv(666,777,888,999,111,222,0.3,0.4)
            initial=before32(out)
            self.assertEqual(self.resolve(u,v,ctypes.byref(out)),0)
            self.assertEqual(before32(out),initial)

    def test_invalid_integer_texels_refused_without_mutation(self):
        for x,y in ((1024,0),(0,1024),(9999,0),(0,9999),
                    (0xffffffff,0xffffffff)):
            out=PageUv(666,777,888,999,111,222,0.3,0.4)
            initial=before32(out)
            self.assertEqual(self.resolve_int(x,y,ctypes.byref(out)),0)
            self.assertEqual(before32(out),initial)

    def test_null_destination_refused(self):
        self.assertEqual(self.resolve(0.25,0.25,None),0)
        self.assertEqual(self.resolve_int(0,0,None),0)

    def test_float_uv_pixel_centers_are_inside_page(self):
        for px in range(4):
            for py in range(4):
                for lx,ly in ((0,0),(255,0),(0,255),(255,255)):
                    got=self.resolve_uv((px*PAGE+lx+0.5)/EDGE,
                                        (py*PAGE+ly+0.5)/EDGE)
                    self.assertEqual((got.page_x,got.page_y),(px,py))
                    self.assertEqual((got.local_x,got.local_y),(lx,ly))

    def test_each_page_distinct_color_signature_in_real_c_decoder(self):
        seen=set()
        for py in range(4):
            for px in range(4):
                image=(ctypes.c_uint8*(PAGE*PAGE*4))()
                info=PixelInfo()
                code=self.decode_page(self.source_c,len(self.source),
                                      px,py,image,len(image),ctypes.byref(info))
                self.assertEqual(code,1)
                self.assertEqual((info.width,info.height),(256,256))
                pixels=bytes(image)
                signature=pixels[4*((89*PAGE)+37):4*((89*PAGE)+38)]
                seen.add(signature)
                at=((py*PAGE+89)*EDGE+px*PAGE+37)*4
                self.assertEqual(signature,self.whole[at:at+4])
        self.assertGreaterEqual(len(seen),8)

    def test_uv_page_sampling_matches_full_1024_c_decoder_at_all_seams(self):
        cache={}
        for y in UV_CENTERS:
            for x in UV_CENTERS:
                page=self.resolve_uv((x+0.5)/EDGE,(y+0.5)/EDGE)
                key=(page.page_x,page.page_y)
                if key not in cache:
                    result=(ctypes.c_uint8*(PAGE*PAGE*4))()
                    info=PixelInfo()
                    self.assertEqual(self.decode_page(
                        self.source_c,len(self.source),
                        *key,result,len(result),ctypes.byref(info)),1)
                    cache[key]=bytes(result)
                offset=4*(page.local_y*PAGE+page.local_x)
                actual=cache[key][offset:offset+4]
                offset_atlas=4*(y*EDGE+x)
                expected=self.whole[offset_atlas:offset_atlas+4]
                self.assertEqual(actual,expected)

    def test_xy_mapping_has_top_left_dds_row_origin(self):
        upper=self.resolve_uv(0.1,0.0001)
        lower=self.resolve_uv(0.1,0.9999)
        self.assertEqual(upper.page_y,0)
        self.assertEqual(lower.page_y,3)
        self.assertEqual(upper.local_y,0)
        self.assertEqual(lower.local_y,255)

    def test_alpha_transparent_palette_near_boundary_not_lost(self):
        cache={}
        saw_transparent=False
        for x,y in ((255,255),(256,255),(255,256),(256,256),
                    (511,511),(512,512),(767,768),(768,767)):
            address=self.resolve_x_y(x,y)
            key=(address.page_x,address.page_y)
            if key not in cache:
                buffer=(ctypes.c_uint8*(PAGE*PAGE*4))()
                metadata=PixelInfo()
                self.assertEqual(self.decode_page(
                    self.source_c,len(self.source),*key,buffer,
                    len(buffer),ctypes.byref(metadata)),1)
                cache[key]=bytes(buffer)
            offset=4*(address.local_y*PAGE+address.local_x)
            pixel=cache[key][offset:offset+4]
            self.assertEqual(pixel,self.whole[4*(y*EDGE+x):4*(y*EDGE+x)+4])
            saw_transparent|=(pixel[3]==0)
        self.assertTrue(saw_transparent)

    def test_all_1024_integer_x_boundary_y_positions(self):
        for y in SEAMS:
            for x in range(EDGE):
                sample=self.resolve_x_y(x,y)
                self.assertEqual(sample.page_x,x//PAGE)
                self.assertEqual(sample.page_y,y//PAGE)
                self.assertEqual(sample.local_u,(x%PAGE+0.5)/PAGE)

    def test_repeatable_output_same_input(self):
        left=self.resolve_uv(.375,.625)
        right=self.resolve_uv(.375,.625)
        self.assertEqual(before32(left),before32(right))

    def test_struct_has_only_simple_numeric_fields(self):
        self.assertEqual(ctypes.sizeof(PageUv),32)
        self.assertEqual([f for f,_ in PageUv._fields_][:6],
                         ["atlas_x","atlas_y","page_x","page_y","local_x","local_y"])


if __name__=="__main__":
    unittest.main()
