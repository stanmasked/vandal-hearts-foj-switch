"""Stage 202: invented-only marker and guest-cycle checks (no copyrighted art)."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.foj_stage202_nexium_actor_endurance_check import (
    SCHEMA, labels, read_rss, check_records, verify
)


def madeup_record(points):
    return ((1280,720),{
        "original_data_experimental":750,
        "secondary_accepted":720,
        "secondary_rejected":0,
        "crossfade":0,
    },frozenset(points))


def invented_records(cycles=6):
    shapes={
        "baseline":range(10,170),
        "reset":range(10,170),
        "a-step":range(90,250),
        "a-paused":range(90,250),
        "b-complete":range(170,330),
        "a-return":range(250,410),
    }
    rec={"baseline":madeup_record(shapes["baseline"])}
    for cycle in range(1,cycles+1):
        for state in ("reset","a-step","a-paused","b-complete","a-return"):
            rec[f"{state}-{cycle:02d}"]=madeup_record(shapes[state])
    return rec


class Stage202EnduranceChecks(unittest.TestCase):
    def setUp(self):
        self.records=invented_records()
        self.memory=[400000,401000,402000,403000,404000,403000,405000]

    def test_six_complete_repeatable_generated_cycles(self):
        r=check_records(self.records,self.memory,6)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["cycles_verified"],6)
        self.assertEqual(r["guest_frames_verified"],31)
        self.assertEqual(r["max_paused_guest_changed_pixels"],0)
        self.assertEqual(r["max_intercycle_repetition_changed_pixels"],0)
        self.assertFalse(r["original_game_animation_fidelity_verified"])
        self.assertFalse(r["rss_leak_freedom_proven"])

    def test_cycle_count_bounds_and_missing_frame(self):
        for value in (0,1,2,9,True,1.1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    labels(value)
        self.records.pop("b-complete-04")
        with self.assertRaises(ValueError):
            check_records(self.records,self.memory,6)

    def test_frozen_animation_does_not_count_as_endurance(self):
        for cycle in range(1,7):
            self.records[f"a-step-{cycle:02d}"]=self.records["baseline"]
        with self.assertRaisesRegex(ValueError,"stopped moving"):
            check_records(self.records,self.memory,6)

    def test_guest_pause_must_remain_still(self):
        self.records["a-paused-04"]=madeup_record(range(350,510))
        with self.assertRaisesRegex(ValueError,"Paused guest"):
            check_records(self.records,self.memory,6)

    def test_intercycle_drift_fails(self):
        self.records["a-return-04"]=madeup_record(range(460,620))
        with self.assertRaisesRegex(ValueError,"cycle no longer repeats"):
            check_records(self.records,self.memory,6)

    def test_bad_sd_asset_or_secondary_marker_fails(self):
        rec=copy.deepcopy(self.records)
        record=rec["reset-02"]
        record[1]["secondary_accepted"]=0
        with self.assertRaisesRegex(ValueError,"Bad research SD"):
            check_records(rec,self.memory,6)

    def test_unexpected_fade_status_in_finished_cycle_fails(self):
        self.records["b-complete-05"][1]["crossfade"]=800
        with self.assertRaisesRegex(ValueError,"Bad research SD"):
            check_records(self.records,self.memory,6)

    def test_memory_growth_outside_budget_fails(self):
        large=self.memory[:]
        large[-1]=self.memory[0]*2+128*1024+1
        with self.assertRaisesRegex(ValueError,"RSS exceeded"):
            check_records(self.records,large,6)

    def test_rss_file_order_and_positive_numeric_fields(self):
        with tempfile.TemporaryDirectory() as path:
            src=Path(path)/"rss.tsv"
            src.write_text("00\t400000\n01\t420000\n02\t430000\n",
                           encoding="ascii")
            self.assertEqual(read_rss(src,2),[400000,420000,430000])
            for data in ("01\t400000\n00\t500000\n02\t530000\n",
                         "00\t0\n01\t2\n02\t3\n",
                         "00\t400000\n01\tnan\n02\t430000\n",
                         "00\t400000\n01\t420000\n"):
                src.write_text(data,encoding="ascii")
                with self.assertRaises(ValueError):
                    read_rss(src,2)

    def test_report_never_includes_original_files_or_geometry(self):
        text=json.dumps(check_records(self.records,self.memory,6))
        for term in (".banim",".fojrm","ps3_xy","bone_weights",
                     "/mnt/","npeb00148","source_image"):
            self.assertNotIn(term,text.lower())


if __name__=="__main__":
    unittest.main()
