"""Stage274 real C11 end-to-end host contract on invented actor/DDS bytes.

Uses the production C modules for orthographic projection, canonical draw
ranges, overlap topology, alpha pass state and DDS decoding. A pass here is
NOT evidence of NeXium GPU rendering, which has a separate mandatory job.
"""
from __future__ import annotations
import ctypes as c
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import COOL
from tools.foj_stage271_generated_negative_sd import rejected_actor
from tools.foj_stage273_dynamic_gpu_sd import (
    CASES, BACK_TO_FRONT, VERTEX_START, VERTEX_STRIDE, generated_actor,
)
from tools.foj_stage274_pass_contract_check import expected_receipt

ROOT=Path(__file__).resolve().parents[2]
U32=c.c_uint32
SIZE=c.c_size_t


class TexturedVertex(c.Structure):
    _fields_=[(name,c.c_float) for name in ("x","y","z","u","v")]


class Section(c.Structure):
    _fields_=[("first_vertex",SIZE),("vertex_count",SIZE),
              ("texture_index",c.c_uint)]


class Camera(c.Structure):
    _fields_=[(name,c.c_float) for name in (
        "center_x","center_y","center_z","extent","yaw","pitch","zoom"
    )]+[("flip_v",c.c_int)]


class Vertex(c.Structure):
    _fields_=[(name,c.c_float) for name in ("x","y","z","w","u","v")]


class Batch(c.Structure):
    _fields_=[(name,U32) for name in (
        "first_vertex","vertex_count","texture_index")]


class StreamInfo(c.Structure):
    _fields_=[("vertices_written",SIZE),("batches_written",SIZE),
              ("camera_depth_min",c.c_float),
              ("camera_depth_max",c.c_float)]


class DrawRange(c.Structure):
    _fields_=Batch._fields_[:2]+[("material_index",U32)]


class AlphaPass(c.Structure):
    _fields_=[(name,U32) for name in (
        "first_vertex","vertex_count","material_index",
        "blend_enabled","depth_test_enabled","depth_write_enabled")]


class AtlasInfo(c.Structure):
    _fields_=[("width",c.c_uint),("height",c.c_uint),
              ("pixel_bytes",SIZE)]


def compile_pipeline(compiler:str, output:Path):
    subprocess.run([
        compiler,"-std=c11","-O2","-Wall","-Wextra","-Werror",
        "-pedantic","-shared","-fPIC","-Icore","-Igpu",
        "core/gpu_vertex_stream.c","core/gpu_draw_plan.c",
        "gpu/transparency_sort.c","gpu/alpha_pass_contract.c",
        "gpu/atlas_dds.c","gpu/alpha_material_contract.c",
        "-lm","-o",str(output),
    ],cwd=ROOT,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    lib=c.CDLL(str(output))
    def bind(name,inputs):
        f=getattr(lib,name)
        f.argtypes=inputs
        f.restype=c.c_int
        return f
    return {
        "project":bind("foj_gpu_prepare_stream",[
            c.POINTER(TexturedVertex),SIZE,c.POINTER(Section),SIZE,
            SIZE,c.POINTER(Camera),c.c_uint,c.c_uint,
            c.POINTER(Vertex),SIZE,c.POINTER(Batch),SIZE,
            c.POINTER(StreamInfo)]),
        "ranges":bind("foj_gpu_build_draw_plan",[
            c.POINTER(Batch),SIZE,SIZE,SIZE,
            c.POINTER(DrawRange),SIZE]),
        "sort":bind("foj_alpha_sort_back_to_front",[
            c.POINTER(Vertex),SIZE,c.POINTER(U32),SIZE]),
        "state":bind("foj_gpu_alpha_pass_contract",[
            c.POINTER(DrawRange),SIZE,c.POINTER(U32),SIZE,
            c.POINTER(AlphaPass),SIZE]),
        "receipt":bind("foj_gpu_alpha_pass_format_receipt",[
            c.POINTER(AlphaPass),SIZE,c.POINTER(c.c_char),SIZE]),
        "decode":bind("foj_atlas_dds_decode",[
            c.POINTER(c.c_uint8),SIZE,c.POINTER(c.c_uint8),SIZE,
            c.POINTER(AtlasInfo)]),
        "opaque":bind("foj_gpu_opaque_rear_atlas",[
            c.POINTER(c.c_uint8),c.POINTER(AtlasInfo)]),
    }


class Stage274ActualNativeChain(unittest.TestCase):
    @staticmethod
    def input_vertices(actor:bytes):
        return (TexturedVertex*9)(*(TexturedVertex(
            *struct.unpack_from("<5f",actor,VERTEX_START+i*VERTEX_STRIDE))
            for i in range(9)))

    def check_chain(self,native,actor:bytes,expected):
        projected=(Vertex*9)()
        batches=(Batch*3)()
        info=StreamInfo()
        camera=Camera(0.,0.,0.,2.,0.,0.,1.,0)
        sections=(Section*3)(
            Section(0,3,0),Section(3,3,1),Section(6,3,2))
        self.assertEqual(native["project"](
            self.input_vertices(actor),9,sections,3,3,
            c.byref(camera),1280,720,projected,9,batches,3,
            c.byref(info)),0)
        self.assertEqual((info.vertices_written,info.batches_written),(9,3))
        ranges=(DrawRange*3)()
        self.assertEqual(native["ranges"](batches,3,9,3,ranges,3),0)
        self.assertEqual([x.material_index for x in ranges],[0,1,2])
        order=(U32*3)(777,777,777)
        status=native["sort"](projected,3,order,3)
        if expected is None:
            self.assertEqual(status,2,"Crossing/coplanar actor not refused")
            self.assertEqual(tuple(order),(777,777,777))
            return
        self.assertEqual(status,0)
        self.assertEqual(tuple(order),expected)
        passes=(AlphaPass*3)()
        self.assertEqual(native["state"](ranges,3,order,3,passes,3),0)
        self.assertEqual(
            [(p.material_index,p.blend_enabled,
              p.depth_test_enabled,p.depth_write_enabled) for p in passes],
            [(2,0,1,1),(expected[1],1,1,0),(expected[2],1,1,0)])
        receipt=c.create_string_buffer(128)
        self.assertEqual(native["receipt"](passes,3,receipt,128),1)
        return receipt.value

    def test_real_c_projection_sort_batch_state_and_dds_both_compilers(self):
        for compiler in ("gcc","clang"):
            with self.subTest(compiler=compiler),tempfile.TemporaryDirectory() as tmp:
                native=compile_pipeline(compiler,Path(tmp)/"libactor.so")
                for case in CASES:
                    with self.subTest(case=case):
                        bytes_written=self.check_chain(
                            native,generated_actor(case),BACK_TO_FRONT[case])
                        self.assertEqual(bytes_written,expected_receipt(case))
                # A fixed-order refusal is not necessarily an alpha cycle:
                # Stage271's reversed actor can instead be sorted safely.
                self.assertEqual(self.check_chain(
                    native,rejected_actor("reversed"),(2,0,1)),
                    expected_receipt("reversed"))
                for negative in ("crossing","coplanar"):
                    with self.subTest(negative=negative):
                        self.check_chain(native,rejected_actor(negative),None)

                dds=generated_dds((*COOL,255))
                source=(c.c_uint8*len(dds)).from_buffer_copy(dds)
                decoded=(c.c_uint8*(256*256*4))()
                meta=AtlasInfo()
                self.assertEqual(native["decode"](
                    source,len(dds),decoded,len(decoded),c.byref(meta)),1)
                self.assertEqual(native["opaque"](decoded,c.byref(meta)),1)
                # No early or late translucent rear material may pass.
                for alpha in (254,0):
                    altered=bytearray(dds)
                    altered[128+3]=alpha
                    src=(c.c_uint8*len(altered)).from_buffer_copy(altered)
                    self.assertEqual(native["decode"](
                        src,len(altered),decoded,len(decoded),c.byref(meta)),1)
                    self.assertEqual(native["opaque"](decoded,c.byref(meta)),0)


if __name__=="__main__":
    unittest.main()
