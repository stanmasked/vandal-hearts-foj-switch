# Stage244 — paired threat-forecast cost inside one NeXium guest

The preceding Stage243 experiment ([merged PR #127](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/127))
compared two executable builds across four separate NeXium processes and
revealed substantial timing differences even where no threat forecast
was active. Those **between-process** differences must not be
misrepresented as game performance gains.

## Method

Only the **optional new research-only** NRO target
`build/foj-isometric-inprocess-pair.nro` enables Stage244's module.
Production/default `foj-isometric-research.nro` remains unchanged.

While the hero is selected and the synthetic movement-danger display is
visible, the module makes **both types of threat forecast in the same
emulated AArch64 process, on an immutable input state**. It keeps a
private probe cache separate from the real rendering/production cache.
Before timing, the probe cache is *warmed* to exclude its initial
calculation. Each pair measures 16 warm-cache calls and 16 uncached
recalculations, reversing call order between consecutive pairs (AB/BA).

Thirty-two consecutive pairs provide one sample window (512 calls
per mode). All preview results, including the warmup, must be byte
identical; a mismatch invalidates measurement rather than risking
display of stale gameplay. The experiment resets on loss of selection,
overlay-hidden state or meaningful battle-state changes (cursor movement
alone intentionally leaves the threat cache valid). Invalid clocks,
unsigned overflow, zero / saturated values, and too-small drawing
buffers fail closed.

The instrumented NRO paints **two independent 24-bit nanosecond-per-call
barcodes**, plus a status tile, outside the previous guest HUD. These
pixels are drawn *after* the ordinary software rendering time is
measured, and do not modify battle rules, the real cache, or replay.
The real NeXium auditor must capture and independently decode both bars
for five selected/visible battle scenes, verify they are inactive for
the other four states, and still satisfy the Stage238 cache/transitions
and Stage241 software-render evidence checks on the same nine PNGs.

## What these measurements do not prove

Within-process AB/BA eliminates the need to compare separate NeXium
launches, and alternating order helps mitigate monotonic timing drift.
It does **not** eliminate host scheduling noise, CPU temperature,
instruction-cache effects, compiler optimization artefacts, or the
perturbation caused by the microbenchmark itself.

These numbers measure only the two `foj_battle_preview_movement_threat`
calculation paths in a generated 8×6 tactical demonstration.
They are **not** game FPS, complete CPU frame time, GPU presentation
cost, physical Nintendo Switch measurements, the original PS3
Vandal Hearts: Flames of Judgment engine, AI or copyrighted game assets.

A large observed uncached/cache ratio describes **per-call synthetic
forecast cost inside this emulator**, not a demonstrated overall game
speedup. The merge gate requires real guest screenshots, unmodified
gameplay state, strict C11, UBSan, and the existing CI compatibility tests.
