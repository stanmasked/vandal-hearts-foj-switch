"""Stage239 negative controls: do not mistake invented speedup for evidence."""
from __future__ import annotations

import copy
import statistics
import unittest

from tools.foj_stage239_cost_check import CALLS, validate_report


def valid_report():
    baseline=[100000,110000,120000,130000,140000]
    cached=[4000,5000,6000,7000,8000]
    return {
        "schema": "foj-stage239-host-threat-cost-v1",
        "source": "generated-research-tactical-simulation",
        "timing_source": "CLOCK_MONOTONIC",
        "platform": "CI Linux host; not Switch or NeXium",
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
        "switch_fps_measured": False,
        "host_wall_time_not_cpu_cycles": True,
        "grid_width": 8,
        "grid_height": 6,
        "cursor_passes": 8,
        "calls_per_trial": CALLS,
        "trials": 5,
        "baseline_forecast_computations": CALLS,
        "cached_forecast_computations": 1,
        "cached_hits": CALLS-1,
        "digests_identical": True,
        "digest": "1234567890abcdef",
        "baseline_duration_ns": baseline,
        "cached_duration_ns": cached,
        "baseline_median_ns": int(statistics.median(baseline)),
        "cached_median_ns": int(statistics.median(cached)),
        "baseline_median_ns_per_call": round(statistics.median(baseline)/CALLS,3),
        "cached_median_ns_per_call": round(statistics.median(cached)/CALLS,3),
        "observed_host_wall_time_ratio": round(
            statistics.median(baseline)/statistics.median(cached),3),
        "hard_performance_pass_threshold": False,
    }


class HostCostReceiptTests(unittest.TestCase):
    def assert_invalid(self, key, value):
        value_dict=valid_report()
        value_dict[key]=value
        with self.assertRaises(ValueError):
            validate_report(value_dict)

    def test_valid_receipt(self):
        self.assertEqual(validate_report(valid_report())["cached_hits"],CALLS-1)

    def test_false_switch_fps_claim(self):
        self.assert_invalid("switch_fps_measured", True)

    def test_false_original_game_ai_claim(self):
        self.assert_invalid("original_foj_ai_verified",True)

    def test_wrong_cached_hit_count(self):
        self.assert_invalid("cached_hits", CALLS-2)

    def test_wrong_full_recompute_count(self):
        self.assert_invalid("baseline_forecast_computations", CALLS-1)

    def test_wrong_cursor_volume(self):
        self.assert_invalid("calls_per_trial", 48)

    def test_invalid_boolean_value(self):
        self.assert_invalid("digests_identical", 1)

    def test_missing_digest(self):
        self.assert_invalid("digest", "")

    def test_wrong_digest_type(self):
        self.assert_invalid("digest",1234567890)

    def test_missing_timing_sample(self):
        self.assert_invalid("baseline_duration_ns", [10,20,30,40])

    def test_forged_median(self):
        self.assert_invalid("baseline_median_ns", 123)

    def test_negative_timing(self):
        self.assert_invalid("cached_duration_ns", [1,2,-1,3,4])

    def test_boolean_timing_rejected(self):
        self.assert_invalid("cached_duration_ns", [1,2,True,3,4])

    def test_wrong_ns_per_call(self):
        self.assert_invalid("baseline_median_ns_per_call", 9999.0)

    def test_forged_walltime_ratio(self):
        self.assert_invalid("observed_host_wall_time_ratio", 88.8)

    def test_nonfinite_walltime_ratio(self):
        self.assert_invalid("observed_host_wall_time_ratio", float("nan"))

    def test_throughput_gate_rejected(self):
        self.assert_invalid("hard_performance_pass_threshold", True)

    def test_wrong_source(self):
        self.assert_invalid("platform", "Nintendo Switch hardware")

    def test_non_object_rejected(self):
        with self.assertRaises(ValueError):
            validate_report([])

    def test_unobserved_speedup_is_not_a_failure(self):
        # Legitimate noisy host samples may have cached > baseline.
        source=valid_report()
        source["cached_duration_ns"]=[200000,210000,220000,230000,240000]
        source["cached_median_ns"]=220000
        source["cached_median_ns_per_call"]=round(220000/CALLS,3)
        source["observed_host_wall_time_ratio"]=round(120000/220000,3)
        self.assertEqual(validate_report(source)["cached_median_ns"],220000)


if __name__=="__main__":
    unittest.main()
