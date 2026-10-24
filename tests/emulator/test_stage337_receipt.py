"""No ROM or gameplay data: negative evidence fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tools.foj_stage337_receipt import MARKER, check, publish


class TestStage337Receipt(unittest.TestCase):
    def test_valid_and_publish(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            receipt = root / "native.txt"
            receipt.write_bytes(MARKER)
            check(receipt)
            folder = root / "out"
            folder.mkdir()
            publish(receipt, folder)
            self.assertIn('"different_pixels": 0',
                          (folder / "stage337-gpu-readback.json").read_text())
            with self.assertRaises(ValueError):
                publish(receipt, folder)

    def test_progress_is_not_success(self):
        # Numerical milestones are diagnostics only; a stale or synthetic
        # progress log must never become a passing GPU receipt.
        with TemporaryDirectory() as d:
            root = Path(d)
            path = root / "native.txt"
            for stage in (0, 5, 6, 7, 10, 11, 12, 13, 80, 81, 82, 83, 84, 85, 98):
                path.write_text(f"FOJ337P1 stage={stage:02d}\n")
                with self.assertRaises(ValueError):
                    check(path)

    def test_progress_is_not_success(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "native.txt"
            path.write_text("FOJ337P1 stage=07\\n")
            with self.assertRaises(ValueError):
                check(path)

    def test_refuse_forged_or_stale(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            receipt = root / "native.txt"
            for payload in (b"", MARKER + b"\n", MARKER.replace(b"diff=0", b"diff=1"),
                            MARKER.replace(b"pixels=5994", b"pixels=5993")):
                receipt.write_bytes(payload)
                with self.assertRaises(ValueError):
                    check(receipt)
            receipt.write_bytes(MARKER)
            link = root / "link"
            link.symlink_to(receipt)
            with self.assertRaises(ValueError):
                check(link)


if __name__ == "__main__":
    unittest.main()
