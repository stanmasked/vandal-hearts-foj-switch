# Stage239 — measured host cost of tactical threat prediction

Stage238 merged in [PR #122](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/122)
after 16/16 workflows succeeded, including real NeXium screenshots proving
that the Stage237 forecast cache is reused by the actual generated Switch NRO.
No evidence from that stage measured elapsed time or an FPS increase.

## What is measured here

`tests/test_battle_threat_cost.c` uses Linux's
`clock_gettime(CLOCK_MONOTONIC)` to time two **actual C entry points**
against the same generated 8×6 research battle state:

- Baseline: `foj_battle_preview_movement_threat`, forced full forecasting
  on every cursor location.
- Cached: `foj_battle_preview_movement_threat_cached`, using one calculation
  then the already-reviewed cursor-invariant matrix.

Each trial sweeps all 48 grid cursor locations eight times (384 calls).
Five runs alternate baseline-first and cached-first order. Independent
warmups precede the measured runs. The report records every batch duration,
the median nanoseconds, median nanoseconds per call and ratio. The benchmark
checks a deterministic forecast digest at every iteration and fails if
the two strategies disagree, if selection changes gameplay, or if the
cache does not record exactly one computation and 383 hits.

## How to interpret the results

CI reports **elapsed wall-clock nanoseconds on GitHub's Linux host**, not
Nintendo Switch CPU cycles, NeXium emulated CPU timing, whole-frame
render time or a measured FPS improvement. Host scheduling, shared
runners and clock jitter may change a benchmark's magnitude and ratio.
The benchmark intentionally never rejects a build based on a minimum
speedup. Behavioral correctness is enforced separately.

For each Python CI matrix version, artifacts named
`foj-stage239-host-threat-cost-py3.11` and
`foj-stage239-host-threat-cost-py3.13` preserve a JSON report.
The generated JSON is then checked by `tools/foj_stage239_cost_check.py`
against the raw trial samples and exact forecast counts. Twenty independent
Python tests reject missing values, fabricated medians, false Switch
performance claims, invalid cache hits and forged ratios. A real
noise-driven slowdown remains a valid result; no speed threshold is imposed.

A dedicated UBSan run also checks the timing harness for undefined
behavior but is **not** used for meaningful performance numbers.

This is a generated-only tactical prototype. The original PS3 game
is not yet running on Switch. No original PS3 AI, production game
performance or GPU characteristics are inferred from this benchmark.

## Follow-up

Switch-native or emulator-side frame and CPU-time profiling is a
**separate future step**, subject to stable, available timing primitives
and guest evidence. Do not extrapolate host speedup to expected Switch FPS.
