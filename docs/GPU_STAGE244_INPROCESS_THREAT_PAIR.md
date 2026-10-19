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

## First real-guest failure and decoded evidence

The first Stage244 guest workflow
[39295665885](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39295665885)
**successfully** passed strict native C11 GCC/Clang/UBSan tests, built the
experimental NRO and captured all nine real 1280×720 NeXium screenshots.
The final checker stopped on a diagnostic coordinate error before
publishing a receipt: the status was sampled at x759 rather than its
actual screenshot location x748..755, resulting in background RGB
(13,19,33) for the initial state.

The archived [real guest evidence artifact](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39295665885/artifacts/12208066693)
shows **24 distinct bars per measurement**. Each barcode pixel group
is 2–3 columns wide after GUI letterboxing, and the exact center
positions are recorded as literal coordinate tables in the Stage244
checker. The status is now read at x750..752, y13/15/17. These
positions were checked against **all nine screenshots**: five selected
and visible states had a valid green ready/parity tile, while the
initial, hidden, cancelled and ended scenes had the pending tile.

After applying those measured coordinate tables offline, the saved
first guest run decodes:

| Captured state | Warm-cache ns/call | Uncached ns/call |
| --- | ---: | ---: |
| selected | 290 | 347284 |
| hovered | 294 | 351166 |
| restored | 350 | 347249 |
| guarded | 298 | 350965 |
| guard_hovered | 314 | 338300 |

The median over these five snapshot readouts is **298 ns/call** for
a warm cached forecast and **347284 ns/call** for full synthetic
recomputation. The reconstructed values are supported by raw image
pixels but did **not** pass the original CI receipt due to the coordinate
bug; they are preliminary until the corrected workflow finishes
successfully. The very large per-call difference is plausible because
the cache returns an already-computed 8×6 risk map while the uncached
path recomputes paths and speculative turns. It is **not** a measure
of whole game rendering or FPS improvement.

Extra screenshot regression tests preserve measured pixel coordinates,
reject the old wrong-position status, and detect corruption of a
high (23rd) nanosecond bit.

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
