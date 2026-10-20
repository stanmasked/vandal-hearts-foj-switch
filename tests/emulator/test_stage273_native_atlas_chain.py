"""Stage273 real C DDS decode -> rear-opacity contract integration.

This checks the *same invented DDS bytes* installed into the NeXium SD root,
not a hand-authored RGBA buffer. No NeXium execution is claimed by these
host tests. Native source is compiled from the actual repository.
"""
from __future__ import annotations

import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import COOL

ROOT = Path(__file__).resolve().parents[2]
CAPACITY = 256 * 256 * 4
UINT8 = ctypes.c_uint8


class AtlasInfo(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_uint),
        ("height", ctypes.c_uint),
        ("pixel_bytes", ctypes.c_size_t),
    ]


class NativeGeneratedDDSIntegration(unittest.TestCase):
    def test_exact_generated_atlas_acceptance_and_single_pixel_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            library = Path(temporary) / "libstage273-atlas.so"
            subprocess.run(
                [
                    "cc", "-std=c11", "-O2", "-Wall", "-Wextra",
                    "-Werror", "-pedantic", "-fPIC", "-shared",
                    "-Igpu", "gpu/atlas_dds.c",
                    "gpu/alpha_material_contract.c",
                    "-o", str(library),
                ],
                cwd=ROOT, check=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            native = ctypes.CDLL(str(library))
            decode = native.foj_atlas_dds_decode
            decode.argtypes = [
                ctypes.POINTER(UINT8), ctypes.c_size_t,
                ctypes.POINTER(UINT8), ctypes.c_size_t,
                ctypes.POINTER(AtlasInfo),
            ]
            decode.restype = ctypes.c_int
            contract = native.foj_gpu_opaque_rear_atlas
            contract.argtypes = [ctypes.POINTER(UINT8), ctypes.POINTER(AtlasInfo)]
            contract.restype = ctypes.c_int

            def decode_generated(dds: bytes):
                source = (UINT8 * len(dds)).from_buffer_copy(dds)
                output = (UINT8 * CAPACITY)()
                ctypes.memset(output, 0xA5, CAPACITY)
                metadata = AtlasInfo(0, 0, 0)
                result = decode(
                    source, len(dds), output, CAPACITY, ctypes.byref(metadata),
                )
                return result, output, metadata

            opaque_dds = generated_dds((*COOL, 255))
            result, decoded, info = decode_generated(opaque_dds)
            self.assertEqual(result, 1)
            self.assertEqual((info.width, info.height, info.pixel_bytes),
                             (64, 64, 64 * 64 * 4))
            self.assertEqual(contract(decoded, ctypes.byref(info)), 1)
            self.assertEqual(bytes(decoded[:8]), bytes((*COOL, 255)) * 2)

            # Mutate exactly one RGBA alpha byte in an otherwise completely
            # valid generated DDS. Decode still succeeds, but the *native
            # rear-opaque guard* must veto it before any draw command exists.
            altered = bytearray(opaque_dds)
            altered[128 + 3] = 254
            result, decoded, info = decode_generated(bytes(altered))
            self.assertEqual(result, 1)
            self.assertEqual(contract(decoded, ctypes.byref(info)), 0)
            altered[128 + 3] = 0
            result, decoded, info = decode_generated(bytes(altered))
            self.assertEqual(result, 1)
            self.assertEqual(contract(decoded, ctypes.byref(info)), 0)

            # The same decoder refuses corrupted input, without leaving
            # forged valid metadata that might conceal a failed decode.
            result, decoded, info = decode_generated(opaque_dds[:-1])
            self.assertEqual(result, 0)
            self.assertEqual(info.pixel_bytes, 0)
            self.assertEqual(decoded[0], 0xA5)


if __name__ == "__main__":
    unittest.main()
