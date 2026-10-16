"""Generated DKSH fixtures: test deko3d's actual 24+64-byte header layout."""
import struct
import unittest

from tools.validate_dksh import DKSH_MAGIC, DkshError, inspect_dksh


def fixture(stage: int = 0, programs: int = 1) -> bytes:
    data = bytearray(512)
    struct.pack_into("<6I", data, 0, DKSH_MAGIC, 24, 256, 256, 24, programs)
    for i in range(programs):
        # DkshProgramHeader: type, entrypoint, GPRs, constbuf1 offset/size,
        # scratch size, then 40 bytes of type-specific union + reserved.
        struct.pack_into("<6I", data, 24 + i * 64,
                         stage, 0, 8, 0, 0, 0)
    data[256:] = bytes([0xA5]) * 256
    return bytes(data)


class DkshStructureTests(unittest.TestCase):
    def test_original_layout_vertex_and_fragment(self):
        vertex = inspect_dksh(fixture(), expected_stage="vertex")
        self.assertEqual(vertex["format"], "DKSH")
        self.assertEqual(vertex["stages"], ["vertex"])
        self.assertEqual(vertex["program_count"], 1)
        self.assertEqual(vertex["control_bytes"], 256)
        self.assertEqual(vertex["code_bytes"], 256)
        fragment = inspect_dksh(fixture(stage=1), expected_stage="fragment")
        self.assertEqual(fragment["stages"], ["fragment"])

    def test_accepts_two_valid_structural_entries(self):
        result = inspect_dksh(fixture(programs=2))
        self.assertEqual(result["program_count"], 2)
        with self.assertRaisesRegex(DkshError, "exactly one"):
            inspect_dksh(fixture(programs=2), expected_stage="vertex")

    def test_rejects_wrong_stage_and_unknown_requested_stage(self):
        with self.assertRaisesRegex(DkshError, "Expected"):
            inspect_dksh(fixture(stage=0), expected_stage="fragment")
        with self.assertRaisesRegex(DkshError, "Unknown requested"):
            inspect_dksh(fixture(stage=0), expected_stage="rainbow")

    def test_rejects_bad_header_sections_and_program_table(self):
        source = fixture()
        for field, value in [
            (0, 0),     # magic
            (1, 9),     # undersized header
            (1, 28),    # wrongly expanded header
            (2, 257),   # misaligned control
            (3, 255),   # misaligned code
            (4, 999),   # table starts beyond control
            (4, 224),   # table starts inside, but 64B record exceeds
            (4, 25),    # table unaligned
            (5, 0),     # zero programs
            (5, 16),    # 16 records will exceed 256B control
        ]:
            altered = bytearray(source)
            struct.pack_into("<I", altered, field * 4, value)
            with self.assertRaises(DkshError, msg=f"field {field}/{value}"):
                inspect_dksh(bytes(altered))
        with self.assertRaises(DkshError):
            inspect_dksh(source[:-1])
        with self.assertRaises(DkshError):
            inspect_dksh(b"\x00" * 12)

    def test_rejects_bad_program_type_and_code_references(self):
        source = fixture()
        for byte_off, value in [
            (24, 99),   # unrecognized stage
            (28, 256),  # entrypoint at code end
            (36, 255),  # constbuf near code end
        ]:
            altered = bytearray(source)
            struct.pack_into("<I", altered, byte_off, value)
            if byte_off == 36:
                struct.pack_into("<I", altered, 40, 4)
            with self.assertRaises(DkshError):
                inspect_dksh(bytes(altered))


if __name__ == "__main__":
    unittest.main()
