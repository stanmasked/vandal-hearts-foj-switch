"""Stage242: synthetic negative tests for three independent guest receipts.

Correctness is fail-closed, but no arbitrary timing-stability/speed threshold.
"""
from __future__ import annotations

import copy
import hashlib
import unittest

from tools.foj_stage242_repeat_guest_check import (
    SCHEMA, STATES, INPUT_SCHEMA as STAGE241_SCHEMA,
    check_receipt, summarize_reports,
)

NRO_SHA = "a" * 64
NEXIUM_SHA = "b" * 64


def make_receipt(run_id: int, base: int = 8000) -> dict:
    samples = {state: base + run_id * 37 + i * 11
               for i, state in enumerate(STATES)}
    return {
        "schema": STAGE241_SCHEMA,
        "emulator": "NeXium",
        "actual_guest_screenshots": len(STATES),
        "timing_metric": "32-frame averaged software-render duration",
        "unit": "microseconds",
        "clock": "libnx armGetSystemTick + armTicksToNs",
        "measurement_scope": "foj_iso_render_battle_cached_options only",
        "render_us_by_game_state": samples,
        "min_render_us": min(samples.values()),
        "median_render_us": sorted(samples.values())[len(STATES)//2],
        "max_render_us": max(samples.values()),
        "guest_timer_valid_nonzero_unsaturated": True,
        "cache_guest_proof": "foj-stage238-nexium-threat-cache-guest-v1",
        "cache_transition_sequence_valid": True,
        "frame_sha256": {
            state: hashlib.sha256(f"run{run_id}-{state}".encode()).hexdigest()
            for state in STATES
        },
        "guest_frame_latency_measured": False,
        "host_wall_time_measured": False,
        "physical_switch_hardware_tested": False,
        "switch_fps_measured": False,
        "original_ps3_assets_used": False,
        "original_foj_ai_verified": False,
    }


def valid_inputs() -> tuple[dict, dict]:
    return (
        {i: make_receipt(i) for i in (1, 2, 3)},
        {i: (NRO_SHA, NEXIUM_SHA) for i in (1, 2, 3)},
    )


class RepeatGuestProofTests(unittest.TestCase):
    def assert_rejected(self, mutate):
        reports, digests = valid_inputs()
        mutate(reports, digests)
        with self.assertRaises(ValueError):
            summarize_reports(reports, digests)

    def test_valid_three_runs_have_no_fps_claim(self):
        reports, digests = valid_inputs()
        summary = summarize_reports(reports, digests)
        self.assertEqual(summary["schema"], SCHEMA)
        self.assertEqual(summary["independent_guest_processes"], 3)
        self.assertEqual(summary["screenshot_count"], 27)
        self.assertEqual(summary["range_of_run_medians_us"], 74)
        self.assertFalse(summary["switch_fps_measured"])
        self.assertFalse(summary["speedup_or_stability_threshold_enforced"])

    def test_no_arbitrary_speed_stability_gate(self):
        reports, digests = valid_inputs()
        reports[3] = make_receipt(3, base=22000)
        summary = summarize_reports(reports, digests)
        self.assertGreater(summary["relative_range_percent"], 100)

    def test_only_two_runs_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             (reports.pop(3), hashes.pop(3)))

    def test_fourth_spoofed_run_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             (reports.update({4: make_receipt(4)}),
                              hashes.update({4: (NRO_SHA, NEXIUM_SHA)})))

    def test_duplicate_frames_across_guests_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[2].update(
                                 frame_sha256=copy.deepcopy(
                                     reports[1]["frame_sha256"])))

    def test_original_assets_misrepresented(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[2].update(original_ps3_assets_used=True))

    def test_switch_fps_misrepresented(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[2].update(switch_fps_measured=True))

    def test_full_frame_latency_misrepresented(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[1].update(guest_frame_latency_measured=True))

    def test_false_neXium_platform(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[3].update(emulator="Physical Switch"))

    def test_clock_substituted(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[1].update(clock="host wall clock"))

    def test_corrupted_screenshot_digest(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[2]["frame_sha256"].update(initial="not sha"))

    def test_wrong_gpu_digest(self):
        self.assert_rejected(lambda reports, hashes:
                             hashes.update({2: (NRO_SHA, "c" * 64)}))

    def test_mismatched_nro_binary(self):
        self.assert_rejected(lambda reports, hashes:
                             hashes.update({2: ("d" * 64, NEXIUM_SHA)}))

    def test_corrupted_median(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[1].update(median_render_us=123))

    def test_zero_timer_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[1]["render_us_by_game_state"].update(
                                 initial=0))

    def test_saturated_timer_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[3]["render_us_by_game_state"].update(
                                 selected=65535))

    def test_boolean_microseconds_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[3]["render_us_by_game_state"].update(
                                 selected=True))

    def test_static_timer_within_guest_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[2].update(render_us_by_game_state={
                                 state: 8000 for state in STATES}))

    def test_missing_state_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[3]["render_us_by_game_state"].pop(
                                 "guard_hovered"))

    def test_forged_validity_bool_rejected(self):
        self.assert_rejected(lambda reports, hashes:
                             reports[3].update(
                                 guest_timer_valid_nonzero_unsaturated=1))


if __name__ == "__main__":
    unittest.main()
