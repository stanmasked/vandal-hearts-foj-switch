# Stage243 — controlled paired NeXium cache-cost experiment

Stage242 [PR #126](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/126)
showed **22.756% between-run spread** in the median of 32-frame
software-render timing readouts from three independent NeXium guest processes.
Therefore a difference between two unrelated runs is not sufficient to
attribute any performance change to threat-map caching.

## Experimental design

Stage243 compiles the **same generated 8×6 research NRO source** into
two AArch64 binaries. The production/default `foj-isometric-research.nro`
uses the existing Stage237 threat-preview cache. The separate
`foj-isometric-research-uncached.nro` uses the macro
`FOJ_STAGE243_DISABLE_CACHE=1` to pass a NULL cache to
`foj_iso_render_battle_cached_options`. NULL uses the existing,
always-recalculate simulation path; gameplay actions and route rules
are unchanged. The experimental NRO is not added to the default
`make all` target.

A generated 8×8 debug tile at guest framebuffer x=508 distinguishes
cached from uncached builds, outside the Stage229 replay indicator,
Stage238 cache tiles and Stage240 16-bit timing bars. The tile is drawn
**after** the timed software render, so it is not part of the measured
interval. The uncached build must show the permanently invalid,
never-hit cache tiles; cached builds must pass the full Stage238
generation/hit-state sequence.

One CI runner downloads a single SHA-256-recorded NeXium nightly,
then launches **four distinct emulator processes sequentially**, in
the ABBA order cached/uncached/uncached/cached. Each process replays
exactly the same fixed scripted nine-state synthetic battle input
sequence and records nine real screenshots (36 in total).

## First actual A–B–B–A CI diagnosis

The original Stage243 GitHub Actions run
[39281551213](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39281551213)
built both NROs and **booted/captured all four real NeXium guest processes
successfully** (36 PNGs), but the final receipt check failed before
interpreting timing. The checker was looking at GUI x=520, immediately
outside the 8×8 build-identity tile: the actual NeXium screenshots put the
five interior visible columns at **GUI x=515..519**, with y=12..18.
The CI failure printed the unrelated background RGB (13,19,33).

The fix samples all nine interior pixels at x=(516,517,518),
y=(13,15,17). This is derived from and cross-checked against the
*saved real failure artifact*, not from guessed framebuffer coordinates.
Five additional pixel regression tests verify mode colors, rejection of
the opposite mode, prevention of the original x=520 bug and detection of
a single corrupted diagnostic pixel. No gameplay or timing code changed
during this correction.

The audit:
- requires each real image to decode 16 valid (nonzero, unsaturated)
  AArch64 guest timer bits, sampled at the verified NeXium GUI positions;
- verifies the compile-time mode identity tile, including its opposite
  color not being present, and the expected cached/uncached hit markers;
- independently rechecks Stage238 battle and cache generation transitions
  on both cached passes;
- requires *exactly identical synthetic battle scene pixels* at matching
  game states across all four runs in the central 500×360 battlefield
  rectangle (x=550..1049, y=180..539). Two real Stage242 NeXium evidence
  runs verified pixel-for-pixel identity across all nine states in this
  crop; a larger area was unsuitable because mutable guest UI pixels
  appeared along its left boundary;
- verifies two consistent cached NRO SHA-256 values, two consistent
  uncached NRO SHA-256 values, different hashes across the variants,
  and one pinned NeXium archive across all four processes;
- reports, for each of nine scripted scenes, two cached readouts,
  two uncached readouts, mean microseconds for each mode, signed
  uncached-minus-cached difference and observed ratio.

Negative tests reject changed software state, copied screenshots,
swapped modes, inconsistent guest binaries, corrupt timers and missing
scenes. **No minimum speedup threshold** is imposed; a legitimate
uncached win is still reported. A/B order is reversed mid-experiment
to reduce drift confounding, but four guest boots still cannot eliminate
runner scheduling noise or establish a confidence interval.

## Baseline drift control

The real four-guest A–B–B–A artifact from run 39281551213 can be
decoded offline after fixing the mode-tile coordinate. Its first
comparison shows nonzero uncached-minus-cached timing differences in
the initial, hidden, cancelled and ended scenes, where the movement
threat forecast is not used at all. This confirms guest execution
variation is still present even with ABBA sequencing.

The Stage243 JSON report now explicitly includes
`no_forecast_control_difference_us`,
`baseline_guest_drift_observed`, and
`causal_cache_speedup_verified=false`.
These negative controls are **not** used to automatically adjust or
subtract experimental numbers: one cannot assume timing drift is a
constant across distinct scenes or sequential guest processes. No
speedup inference or minimum-threshold gate is allowed from these
data alone.

## Measurement limits

Each decoded microsecond value is the latest **32-frame mean** of
`foj_iso_render_battle_cached_options` only. A screenshot is not an
individual frame-time observation, and measurements exclude
framebuffer presentation, GPU, NeXium host GUI, controls, audio,
VSync and whole-game frame latency. ABBA ratio is limited to this
synthetic prototype, this emulator, and this runner.

No physical Switch performance, original Vandal Hearts: Flames of
Judgment PS3 engine, source-game AI or source assets have been tested.
**No FPS improvement may be claimed** from this experiment.
