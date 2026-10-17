"""Synthetic-only stage 157 tests: no original PS3 game files."""
from collections import defaultdict
import random
import unittest
from unittest.mock import patch

from tools import foj_texture_relations as relations
from tools import foj_resource_table_hypotheses as tables


def old_runs(points, minimum):
    targets = defaultdict(set)
    for pos, dest in points:
        targets[pos].add(dest)
    safe = {p: next(iter(v)) for p, v in targets.items() if len(v) == 1}
    proposed = []
    for stride in tables.SUPPORTED_STRIDES:
        for start in sorted(safe):
            if start - stride in safe:
                continue
            positions = []
            pos = start
            while pos in safe:
                positions.append(pos)
                pos += stride
            dests = [safe[p] for p in positions]
            if len(dests) < minimum or len(set(dests)) < minimum:
                continue
            proposed.append({
                "start_word_offset": start,
                "end_word_offset": positions[-1],
                "stride_bytes": stride,
                "entry_count": len(positions),
                "distinct_dds_targets": len(set(dests)),
                "target_dds_offsets": dests,
                "_positions": positions,
            })
    proposed.sort(key=lambda r: (-r["entry_count"], r["stride_bytes"],
                                  r["start_word_offset"]))
    accepted = []
    for row in proposed:
        if any(set(row["_positions"]).issubset(set(old["_positions"]))
               for old in accepted):
            continue
        accepted.append(row)
    accepted.sort(key=lambda r: (r["start_word_offset"], r["stride_bytes"],
                                 -r["entry_count"]))
    for row in accepted:
        del row["_positions"]
    return accepted


class IndexedSearchTests(unittest.TestCase):
    def test_merged_intervals_match_prior_containment(self):
        rng = random.Random(157)
        for amount in (1, 2, 20, 80):
            for _ in range(10):
                entries = [
                    {"offset": pos,
                     "candidate_span_end": pos + rng.choice((0, 128, 256, 500))}
                    for pos in sorted(rng.randrange(128, 1200)
                                      for _ in range(amount))
                ]
                merged = relations._merged_candidate_spans(entries)
                self.assertTrue(all(a[1] < b[0]
                                    for a, b in zip(merged, merged[1:])))
                for pos in range(0, 2048, 4):
                    old = any(e["offset"] <= pos < (
                        e["candidate_span_end"] or e["offset"] +
                        relations.HEADER_BYTES) for e in entries)
                    new = any(a <= pos < b for a, b in merged)
                    self.assertEqual(old, new)

    def test_randomized_run_pruning_equivalent_to_stage156(self):
        rng = random.Random(157)
        for _ in range(200):
            points = []
            for pos in rng.sample(range(0, 96, 4), rng.randrange(3, 24)):
                points.append((pos, rng.choice([512, 768, 1024, 1536, 2048])))
                if rng.randrange(5) == 0:
                    points.append((pos, rng.choice([512, 768, 1024, 1536])))
            for minimum in (2, 3, 4):
                self.assertEqual(
                    tables._candidate_runs(points, min_distinct=minimum),
                    old_runs(points, minimum))

    def test_2500_disjoint_runs_bound_index_queries(self):
        points = [(i * 64 + delta, 512 + i * 100 + delta)
                  for i in range(2500) for delta in (0, 4, 8)]
        original = tables.bisect_right
        calls = []
        def counted(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)
        with patch.object(tables, "bisect_right", side_effect=counted):
            result = tables._candidate_runs(points, min_distinct=3)
        self.assertEqual(len(result), 2500)
        self.assertLessEqual(len(calls), 6 * len(result))
        self.assertEqual(result[0]["start_word_offset"], 0)
        self.assertEqual(result[-1]["start_word_offset"], 64 * 2499)

    def test_points_limit_refuses_incomplete_result(self):
        with patch.object(tables, "MAX_POINTS_PER_ENDIAN", 2):
            with self.assertRaisesRegex(ValueError, "Too many pointer observations"):
                tables._candidate_runs([(0, 512), (4, 768), (8, 1024)],
                                       min_distinct=3)

    def test_provisional_limit_refuses_incomplete_result(self):
        points = [(i * 64 + d, 512 + i * 100 + d)
                  for i in range(4) for d in (0, 4, 8)]
        with patch.object(tables, "MAX_PROVISIONAL_RUNS", 3):
            with self.assertRaisesRegex(ValueError, "Too many provisional"):
                tables._candidate_runs(points, min_distinct=3)


if __name__ == "__main__":
    unittest.main()
