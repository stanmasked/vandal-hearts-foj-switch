"""Stage 150 uses only synthetic 16 KiB files and private temporary folders."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.foj_stability_matrix import synthetic_sample
import tools.foj_source_coherence_gate as gate


SPEC = (4, 8, "little", "ascending", False)


class SourceCoherenceTests(unittest.TestCase):
    def test_complete_pipeline_and_replay_on_stable_generated_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            synthetic_sample(source, SPEC)
            original = (source / "synthetic.bin").read_bytes()
            reports = gate.examine(source)
            self.assertEqual(len(reports), len(gate.FILE_NAMES))
            final = reports[-1]
            self.assertEqual(final["status"], "two-snapshots-match")
            self.assertTrue(final["summary"]["replay_verified"])
            self.assertEqual(final["summary"]["regular_files"], 1)
            self.assertEqual(final["summary"]["dds_candidates"], 4)
            self.assertEqual(final["summary"]["hypothetical_tables"], 1)
            self.assertFalse(final["summary"]["original_foj_format_proven"])
            self.assertFalse(final["summary"]["switch_hardware_verified"])
            self.assertNotIn("synthetic.bin", json.dumps(final))
            self.assertEqual((source / "synthetic.bin").read_bytes(), original)

    def test_snapshots_are_repeatable_but_not_serialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            first, a = gate.snapshot(root)
            second, b = gate.snapshot(root)
            self.assertEqual(first, second)
            self.assertEqual(a, b)
            self.assertEqual(a["regular_files"], 1)
            self.assertEqual(a["bytes_per_pass"], 16384)
            self.assertTrue(all(not isinstance(v, str)
                                for v in first.values()))

    def test_byte_change_same_inode_during_triage_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            file = root / "synthetic.bin"
            inode = file.stat().st_ino
            original = gate.triage_reports

            def mutate(*args):
                result = original(*args)
                with file.open("r+b") as stream:
                    stream.seek(15000)
                    stream.write(b"Z")
                return result

            with patch.object(gate, "triage_reports", side_effect=mutate):
                with self.assertRaisesRegex(ValueError, "changed"):
                    gate.examine(root)
            self.assertEqual(file.stat().st_ino, inode)

    def test_restore_identical_bytes_with_changed_mtime_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            file = root / "synthetic.bin"
            original = gate.triage_reports

            def mutate_then_restore(*args):
                result = original(*args)
                data = file.read_bytes()
                file.write_bytes(data)
                st = file.stat()
                os.utime(file, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))
                return result

            with patch.object(gate, "triage_reports",
                              side_effect=mutate_then_restore):
                with self.assertRaisesRegex(ValueError, "changed"):
                    gate.examine(root)

    def test_added_and_deleted_source_paths_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            original = gate.triage_reports
            def add(*args):
                result = original(*args)
                (root / "added.bin").write_bytes(b"new")
                return result
            with patch.object(gate, "triage_reports", side_effect=add):
                with self.assertRaisesRegex(ValueError, "changed"):
                    gate.examine(root)
            (root / "added.bin").unlink()

            def delete(*args):
                result = original(*args)
                (root / "synthetic.bin").unlink()
                return result
            with patch.object(gate, "triage_reports", side_effect=delete):
                with self.assertRaisesRegex(ValueError, "changed"):
                    gate.examine(root)

    def test_symlink_and_fifo_are_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            link = root / "linked"
            link.symlink_to(root / "synthetic.bin")
            with self.assertRaisesRegex(ValueError, "Symlink"):
                gate.snapshot(root)
            link.unlink()
            if hasattr(os, "mkfifo"):
                os.mkfifo(root / "pipe")
                with self.assertRaisesRegex(ValueError, "unsupported"):
                    gate.snapshot(root)

    def test_byte_and_file_caps_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            with self.assertRaisesRegex(ValueError, "byte audit limits"):
                gate.snapshot(root, max_total_bytes=1024)
            with self.assertRaises(ValueError):
                gate.snapshot(root, max_files=True)
            (root / "more.txt").write_text("another source file")
            with self.assertRaisesRegex(ValueError, "Too many source"):
                gate.snapshot(root, max_files=1)

    def test_publication_is_private_local_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "source"
            output = base / "reports"
            synthetic_sample(root, SPEC)
            report = gate.publish(root, output)
            self.assertEqual(report["status"], "two-snapshots-match")
            self.assertEqual(
                sorted(f.name for f in output.iterdir()), sorted(gate.FILE_NAMES))
            for name in gate.FILE_NAMES:
                contents = (output / name).read_text(encoding="utf-8")
                self.assertNotIn(str(root), contents)
                # Metadata-only DDS descriptions are expected; binary payloads are not.
                self.assertNotIn("\\u0000", contents)
                self.assertNotIn("\\xff", contents)
                self.assertIsInstance(json.loads(contents), dict)
            with self.assertRaisesRegex(ValueError, "already exist"):
                gate.publish(root, output)
            with self.assertRaisesRegex(ValueError, "outside"):
                gate.publish(root, root / "reports")

    def test_failed_pipeline_cannot_publish_partial_report_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, output = base / "source", base / "reports"
            synthetic_sample(root, SPEC)
            original = gate.triage_reports
            def alter(*args):
                result = original(*args)
                (root / "synthetic.bin").write_bytes(b"change")
                return result
            with patch.object(gate, "triage_reports", side_effect=alter):
                with self.assertRaises(ValueError):
                    gate.publish(root, output)
            self.assertFalse(output.exists())
            self.assertFalse(list(base.glob(".foj-stage150-*")))

    def test_cli_runs_without_absolute_paths_or_source_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, output = base / "source", base / "new-local"
            synthetic_sample(root, SPEC)
            command = [
                sys.executable, "-m", "tools.foj_source_coherence_gate",
                str(root), "--output-dir", str(output),
                "--total-mib", "1"]
            process = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("Source coherence verified: 1 local files",
                          process.stdout)
            self.assertNotIn(str(root), process.stdout)
            self.assertNotIn(str(root), process.stderr)
            self.assertTrue((output / "foj-source-coherence.json").is_file())


if __name__ == "__main__":
    unittest.main()
