"""Stage 160 exact JSON accounting regressions using synthetic metadata only."""
from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import tools.foj_report_transit_budget as transit
from tools.foj_stability_matrix import synthetic_sample
from tools.foj_source_coherence_gate import examine
from tools.foj_stage159_profile import generated_table_manifest
from tools.foj_texture_relations import build_relations
from tools.foj_resource_table_hypotheses import infer_tables


def canonical_size(report):
    return len((json.dumps(report, indent=2, sort_keys=True,
                           ensure_ascii=False, allow_nan=False) + "\n"
                ).encode("utf-8"))


class FastJsonByteAccountingTests(unittest.TestCase):
    def assert_canonical(self, report):
        self.assertEqual(transit.measure_report(report), canonical_size(report))

    def test_all_ascii_json_exact(self):
        self.assert_canonical({
            "schema": "invented",
            "records": [{"a": i, "value": "x" * 24} for i in range(256)],
        })

    def test_unicode_emoji_combining_text_and_long_strings(self):
        self.assert_canonical({
            "accents": "öéç",
            "chinese": "字体日本語漢字",
            "emoji": "🔥🎮🧭",
            "combining": "e\u0301",
            "repeat": "🥇" * 500,
        })

    def test_escaped_control_characters_stay_byte_exact(self):
        self.assert_canonical({
            "quote": 'a"b',
            "backslash": "x\\y",
            "newlines": "\n\r\t\b\f",
            "control": "\x00\x01\x1f",
            "ascii_escape_text": "\\u00e9",
            "non_ascii": "\u2028\u2029",
        })

    def test_nested_json_boolean_integer_null_float(self):
        self.assert_canonical({
            "present": True, "absent": False, "missing": None,
            "large_int": 987654321098765432109876543210,
            "float": -1.125e30,
            "deep": [{"bytes": "sample", "values": [1, None, 4.5]}],
        })

    def test_seeded_mixed_unicode_random_reports(self):
        rng = random.Random(160)
        alphabet = ["a", "R", " ", "\t", "\n", "\"", "\\", "é",
                    "字", "€", "😀", "\u0301", "\x00", "\x7f"]
        for index in range(100):
            label = "".join(rng.choice(alphabet)
                            for _ in range(rng.randrange(1, 40)))
            report = {
                "schema": "synthetic",
                "round": index,
                "values": [{"text": label, "offset": j * 4}
                           for j in range(rng.randrange(1, 12))],
            }
            with self.subTest(index=index):
                self.assert_canonical(report)

    def test_exact_minimum_byte_budget_including_final_newline(self):
        # The 1,024-byte minimum configured budget must remain inclusive.
        report = {"payload": "a" * 1000}
        limit = canonical_size(report)
        self.assertGreaterEqual(limit, 1024)
        self.assertEqual(transit.measure_report(report, limit=limit), limit)
        with self.assertRaisesRegex(ValueError, "byte budget"):
            transit.measure_report(report, limit=limit - 1)

    def test_exact_unicode_boundary_rejects_one_byte_short(self):
        report = {"multi": "😀" * 250, "padding": "xx"}
        limit = canonical_size(report)
        self.assertGreaterEqual(limit, 1024)
        self.assertEqual(transit.measure_report(report, limit=limit), limit)
        with self.assertRaisesRegex(ValueError, "byte budget"):
            transit.measure_report(report, limit=limit - 1)

    def test_never_call_encode_for_ascii_fragments(self):
        class NoAsciiEncoding(str):
            def encode(self, *args, **kwargs):
                raise AssertionError("ASCII fragment unnecessarily encoded")

        class Encoder:
            def __init__(self, **kwargs):
                self.settings = kwargs
            def iterencode(self, data):
                yield NoAsciiEncoding("A" * 1024)

        with patch.object(transit.json, "JSONEncoder", Encoder):
            self.assertEqual(transit.measure_report({"x": "unused"}), 1025)
            with self.assertRaisesRegex(ValueError, "byte budget"):
                transit.measure_report({"x": "unused"}, limit=1024)

    def test_non_ascii_fragments_are_encoded_exactly(self):
        class NonAsciiProbe(str):
            calls = 0
            def encode(self, *args, **kwargs):
                self.calls += 1
                return super().encode(*args, **kwargs)

        fragment = NonAsciiProbe("😀" * 5)
        class Encoder:
            def __init__(self, **kwargs):
                pass
            def iterencode(self, data):
                yield fragment

        with patch.object(transit.json, "JSONEncoder", Encoder):
            self.assertEqual(transit.measure_report({"value": True}), 21)
        self.assertEqual(fragment.calls, 1)

    def test_unpaired_surrogates_fail_with_generic_private_safe_message(self):
        sentinel = "SECRET-PATH-FILENAME"
        bad_report = {"source": sentinel + "\udcff"}
        with self.assertRaisesRegex(ValueError, "Invalid UTF-8") as error:
            transit.measure_report(bad_report)
        self.assertNotIn(sentinel, str(error.exception))
        self.assertNotIn("\\udcff", str(error.exception))

    def test_new_fast_path_keeps_non_finite_numbers_rejected(self):
        for invalid in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=str(invalid)), self.assertRaises(ValueError):
                transit.measure_report({"not_finite": invalid})

    def test_stage_143_generated_report_is_canonical(self):
        input_report = generated_table_manifest(128)
        output_report = infer_tables(input_report)
        self.assert_canonical(input_report)
        self.assert_canonical(output_report)
        self.assertEqual(output_report["summary"]["table_hypotheses"], 128)

    def test_stage_142_generated_file_output_is_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from tools.foj_stage158_benchmark import generated_case
            manifest, prefix = generated_case(root, 32)
            self.assert_canonical(manifest)
            output_report = build_relations(
                manifest, root=root, prefix_bytes=prefix)
            self.assert_canonical(output_report)
            self.assertEqual(output_report["summary"]["dds_candidates"], 32)

    def test_stage_150_pipeline_preserves_report_schemas_and_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "invented-source"
            synthetic_sample(root, (4, 8, "little", "ascending", False))
            reports = examine(root)
            self.assertEqual(len(reports), 7)
            for report in reports:
                self.assert_canonical(report)
            self.assertTrue(reports[-1]["summary"]["replay_verified"])

    def test_read_report_with_unicode_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            source = {"schema": "synthetic", "name": "😀" * 300}
            path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf8")
            self.assertEqual(transit.read_report(path), source)
            path.write_text('{"name": 1, "name": 2}', encoding="utf8")
            with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
                transit.read_report(path)


if __name__ == "__main__":
    unittest.main()
