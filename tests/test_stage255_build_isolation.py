#!/usr/bin/env python3
"""Stage255 isolation and guest proof wiring audit.

Static CI guard, not a substitute for compiling or running a Switch NRO.
Uses no proprietary game content.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "switch" / "Makefile"
GUEST = ROOT / "switch" / "source" / "iso_main.c"
BUDGET = ROOT / "core" / "base_cache_compact.c"
NEXIUM = ROOT / ".github" / "workflows" / "stage255-nexium-budget-fallback.yml"

FLAGS = "-DFOJ_STAGE255_BUDGET_FALLBACK=1"
STAGE254 = "-DFOJ_STAGE254_REUSE=1"
TARGET = "ISO_BUDGET_FALLBACK_TARGET"
PREVIOUS = "ISO_BOUNDED_REUSE_TARGET"


class Stage255BuildIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mk = MAKEFILE.read_text(encoding="utf-8")
        cls.guest = GUEST.read_text(encoding="utf-8")
        cls.cache = BUDGET.read_text(encoding="utf-8")
        cls.ci = NEXIUM.read_text(encoding="utf-8")

    def test_only_one_compiler_command_enables_stage255(self):
        compiler_commands = [
            line.strip() for line in self.mk.splitlines()
            if line.lstrip().startswith("$(CC)")
        ]
        self.assertGreater(len(compiler_commands), 4)
        enabling = [line for line in compiler_commands if FLAGS in line]
        self.assertEqual(len(enabling), 1)
        self.assertIn(STAGE254, enabling[0])
        # Retain all required predecessor guest stages.
        for n in range(246, 256):
            if n in (246, 247, 248, 249, 250, 251, 252, 253, 254):
                self.assertIn(f"-DFOJ_STAGE{n}_", enabling[0])

    def test_separate_target_without_default_build_deps(self):
        self.assertIn(
            f"{TARGET} := build/foj-isometric-compact-budget-fallback", self.mk
        )
        self.assertIn("$(ISO_BUDGET_FALLBACK_TARGET).nro:", self.mk)
        self.assertIn("$(ISO_BOUNDED_REUSE_TARGET).nro:", self.mk)
        # Only the designated target can compile the isolated policy.
        target_start = self.mk.index("$(ISO_BUDGET_FALLBACK_TARGET).elf:")
        target_end = self.mk.index("$(ISO_BUDGET_FALLBACK_TARGET).nro:")
        self.assertIn(FLAGS, self.mk[target_start:target_end])
        preceding = self.mk[:target_start]
        self.assertNotIn(FLAGS, preceding)
        self.assertNotIn("$(ISO_BUDGET_FALLBACK_TARGET).nro:", preceding)
        self.assertEqual(self.mk.count("$(ISO_BUDGET_FALLBACK_TARGET).elf:"), 1)

    def test_guest_only_in_opt_in_guards(self):
        self.assertIn(
            "#if FOJ_STAGE255_BUDGET_FALLBACK\n"
            "#include \"compact_budget_probe.h\"", self.guest
        )
        self.assertEqual(self.guest.count("(void)foj_budget_probe_run("), 1)
        self.assertEqual(self.guest.count("(void)foj_budget_probe_draw("), 1)
        self.assertGreater(
            self.guest.index("(void)foj_budget_probe_run("),
            self.guest.index("(void)foj_reuse_probe_run("),
        )
        self.assertIn(
            '#error "Stage255 budget fallback requires FOJ_STAGE254_REUSE=1"',
            self.cache,
        )

    def test_ci_runs_real_stage255_guest_target_and_decoder(self):
        self.assertIn(
            "make -f switch/Makefile "
            "build/foj-isometric-compact-budget-fallback.nro", self.ci
        )
        self.assertIn(
            "FOJ_NRO=\"$GITHUB_WORKSPACE/nros/"
            "foj-isometric-compact-budget-fallback.nro\"", self.ci
        )
        self.assertIn(
            "python3 -m tools.foj_stage255_budget_guest_check", self.ci
        )
        for state in (
            "initial", "selected", "hovered", "hidden", "restored",
            "cancelled", "guarded", "guard-hovered", "ended",
        ):
            self.assertRegex(
                self.ci,
                r"--" + re.escape(state) + r"\s+guest-evidence/cache-",
            )


if __name__ == "__main__":
    unittest.main()
