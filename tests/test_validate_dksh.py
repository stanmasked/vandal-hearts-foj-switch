"""Generated DKSH container tests; no actual console/publisher shaders."""
import struct
import unittest

from tools.validate_dksh import DKSH_MAGIC, DkshError, inspect_dksh


def fixture() -> bytes:
    data = bytearray(512)
    struct.pack_into("<6I", data, 0, DKSH_MAGIC, 24, 256, 256, 24, 1)
    data[256:] = bytes([0xA5]) * 256
    return bytes(data)


class DkshStructureTests(unittest.TestCase):
    def test_valid_generated_aligned_container(self):
        result = inspect_dksh(fixture())
        self.assertEqual(result["format"], "DKSH")
        self.assertEqual(result["program_count"], 1)
        self.assertEqual(result["control_bytes"], 256)
        self.assertEqual(result["code_bytes"], 256)

    def test_rejects_unaligned_and_corrupted_structures(self):
        source = fixture()
        for field, value in [
            (0, 0),     # magic
            (1, 9),     # undersized header
            (2, 257),   # misaligned control
            (3, 255),   # misaligned code
            (4, 999),   # program table beyond control
            (5, 0),     # zero programs
        ]:
            altered = bytearray(source)
            struct.pack_into("<I", altered, field * 4, value)
            with self.assertRaises(DkshError, msg=f"field {field}"):
                inspect_dksh(bytes(altered))
        with self.assertRaises(DkshError):
            inspect_dksh(source[:-1])
        with self.assertRaises(DkshError):
            inspect_dksh(b"\x00" * 12)


if __name__ == "__main__":
    unittest.main()
