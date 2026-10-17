"""Stage-154 replay tests use invented bytes in disposable temporary folders."""
from contextlib import contextmanager
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tools.foj_fd_bound_reader as reader
import tools.foj_texture_probe as scanner
from tools.foj_source_coherence_gate import examine, publish
from tools.foj_stability_matrix import synthetic_sample

SPEC = (4, 8, "little", "ascending", False)


class DdsTwoPassIntegrityTests(unittest.TestCase):
    def test_stable_dds_stream_and_full_source_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            first = scanner.inventory(root)
            self.assertEqual(first["files_scanned"], 1)
            self.assertEqual(len(first["candidates"]), 4)
            self.assertEqual(first, scanner.inventory(root))
            self.assertEqual(len(list(scanner.iter_candidate_headers(
                root / "synthetic.bin"))), 4)
            replay = examine(root)
            self.assertTrue(replay[-1]["summary"]["replay_verified"])
            self.assertNotIn("sha256", json.dumps(first).lower())

    def test_mutation_between_complete_passes_fails_even_with_same_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            asset = root / "synthetic.bin"
            initial_size = asset.stat().st_size
            inode = asset.stat().st_ino
            replay = scanner._replay_file_hash
            changed = []

            def flip_before_readback(stream, *, size):
                if not changed:
                    changed.append(True)
                    with asset.open("r+b") as handle:
                        handle.seek(14000)
                        handle.write(b"X")
                return replay(stream, size=size)

            # Drop timestamp-based detection only *inside this test* so the
            # failure specifically proves the new content-digest gate works.
            with patch.object(reader, "_identity",
                              side_effect=lambda st: (st.st_dev, st.st_ino,
                                                      st.st_mode, st.st_size)):
                with patch.object(scanner, "_replay_file_hash",
                                  side_effect=flip_before_readback):
                    with self.assertRaisesRegex(ValueError, "bytes changed"):
                        scanner.inventory(root)
            self.assertTrue(changed)
            self.assertEqual(asset.stat().st_size, initial_size)
            self.assertEqual(asset.stat().st_ino, inode)

    def test_change_after_initial_dds_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            asset = root / "synthetic.bin"
            original = scanner._iter_headers_stream
            changed = []

            def mutate_after_first_header(stream, **kwargs):
                for header in original(stream, **kwargs):
                    yield header
                    if not changed:
                        changed.append(True)
                        with asset.open("r+b") as handle:
                            handle.seek(14000)
                            handle.write(b"Y")

            with patch.object(reader, "_identity",
                              side_effect=lambda st: (st.st_ino, st.st_size)):
                with patch.object(scanner, "_iter_headers_stream",
                                  side_effect=mutate_after_first_header):
                    with self.assertRaisesRegex(ValueError, "bytes changed"):
                        scanner.inventory(root)
            self.assertEqual(len(changed), 1)

    def test_zero_candidate_files_are_still_fully_replayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "no-texture.bin"
            file.write_bytes(b"\xfe" * (2 * 1024 * 1024))
            expected = file.stat().st_size
            replay = scanner._replay_file_hash
            counts = []

            def observed_replay(stream, *, size):
                counts.append(size)
                return replay(stream, size=size)

            with patch.object(scanner, "_replay_file_hash",
                              side_effect=observed_replay):
                result = scanner.inventory(root)
            self.assertEqual(result["candidates"], [])
            self.assertEqual(result["files_scanned"], 1)
            self.assertEqual(counts, [expected])

    def test_reaching_header_cap_does_not_skip_tail_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            asset = root / "synthetic.bin"
            replay = scanner._replay_file_hash
            changed = []

            def mutate_unscanned_tail(stream, *, size):
                changed.append(True)
                with asset.open("r+b") as handle:
                    handle.seek(15000)
                    handle.write(b"Z")
                return replay(stream, size=size)

            with patch.object(reader, "_identity",
                              side_effect=lambda st: (st.st_ino, st.st_size)):
                with patch.object(scanner, "_replay_file_hash",
                                  side_effect=mutate_unscanned_tail):
                    with self.assertRaisesRegex(ValueError, "bytes changed"):
                        scanner.inventory(root, max_hits_per_file=1)
            self.assertTrue(changed)

    def test_replay_detects_truncation_and_growth(self):
        original = b"\xff" * 1024
        for second in (original[:-1], original + b"z"):
            with self.subTest(second_size=len(second)):
                class ChangingStream:
                    def __init__(self):
                        self.stream = io.BytesIO(original)
                        self.generation = 0
                    def read(self, count=-1):
                        return self.stream.read(count)
                    def seek(self, offset, whence=0):
                        self.generation += 1
                        self.stream = io.BytesIO(second)
                        return self.stream.seek(offset, whence)
                with self.assertRaisesRegex(ValueError, "size changed|grew"):
                    scanner._verified_header_candidates(
                        ChangingStream(), file_bytes=len(original), max_hits=1)

    def test_no_partial_coherence_publication_on_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, output = base / "source", base / "private-reports"
            synthetic_sample(root, SPEC)
            file = root / "synthetic.bin"
            original = scanner._replay_file_hash

            def mutate(stream, *, size):
                with file.open("r+b") as handle:
                    handle.seek(14000)
                    handle.write(b"X")
                return original(stream, size=size)

            with patch.object(reader, "_identity",
                              side_effect=lambda st: (st.st_ino, st.st_size)):
                with patch.object(scanner, "_replay_file_hash",
                                  side_effect=mutate):
                    with self.assertRaises(ValueError):
                        publish(root, output)
            self.assertFalse(output.exists())

    def test_read_bounded_prefix_compares_two_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "invented.bin"
            file.write_bytes(b"abcd")
            self.assertEqual(reader.read_bounded_prefix(root, "invented.bin", 4),
                             b"abcd")
            real_open = reader.open_regular_beneath

            class ChangingReader:
                def __init__(self, original):
                    self.original = original
                    self.reads = 0
                def read(self, limit):
                    self.reads += 1
                    if self.reads == 2:
                        with file.open("r+b") as handle:
                            handle.seek(0)
                            handle.write(b"wxyz")
                    return self.original.read(limit)
                def seek(self, *args, **kwargs):
                    return self.original.seek(*args, **kwargs)

            @contextmanager
            def altered(root_path, rel):
                with real_open(root_path, rel) as (stream, metadata):
                    yield ChangingReader(stream), metadata

            with patch.object(reader, "_identity",
                              side_effect=lambda st: (st.st_ino, st.st_size)):
                with patch.object(reader, "open_regular_beneath",
                                  side_effect=altered):
                    with self.assertRaisesRegex(ValueError, "prefix bytes changed"):
                        reader.read_bounded_prefix(root, "invented.bin", 4)

    def test_direct_iterator_verifies_before_yielding_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            synthetic_sample(root, SPEC)
            file = root / "synthetic.bin"
            replay = scanner._replay_file_hash

            def mutate(stream, *, size):
                with file.open("r+b") as fp:
                    fp.seek(14000)
                    fp.write(b"W")
                return replay(stream, size=size)

            with patch.object(reader, "_identity",
                              side_effect=lambda st: (st.st_ino, st.st_size)):
                with patch.object(scanner, "_replay_file_hash",
                                  side_effect=mutate):
                    with self.assertRaisesRegex(ValueError, "bytes changed"):
                        list(scanner.iter_candidate_headers(file))

    def test_max_hit_count_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "anything.bin").write_bytes(b"\xff")
            for n in (0, -1, True, 4097):
                with self.subTest(value=n), self.assertRaises(ValueError):
                    scanner.inventory(root, max_hits_per_file=n)


if __name__ == "__main__":
    unittest.main()
