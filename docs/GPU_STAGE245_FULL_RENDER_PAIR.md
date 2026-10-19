# Stage245 — total CPU software-render cost, paired inside NeXium

Stage244 ([merged PR #128](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/128))
measured around 290 ns for a warm forecast-cache lookup versus 339,016 ns
for an uncached synthetic movement-threat calculation. Those microbenchmarks
do not tell us how much time is saved by a *complete* game draw.

## Controlled experiment

The new **opt-in only** research NRO
`build/foj-isometric-full-render-pair.nro` draws the same generated
8×6 isometric battle **twice per frame**, using two independent private
1280×720 output buffers. In one pass it invokes the original
`foj_iso_render_battle_cached_options` function with a warmed private
threat cache; in the other pass it calls the same function with a NULL
cache. The production game framebuffer and real gameplay cache remain
untouched.

A 32-pair measurement window alternates order cached/uncached and
uncached/cached on consecutive pairs (AB/BA). The two outputs must match
**byte for byte across the entire full framebuffer**; a mismatch shuts
off the measurement. It resets when the battle semantics change, but not
when only the hovered cursor moves, just as the production cache does.
There is no randomized condition mixing or inference across guest boots.

Both 16-bit barcode values report *microseconds per complete software
render function call*. Stage245 draws those values and a ready/parity
status tile at guest framebuffer x=780, 852 and 924 in the HUD row.
They are drawn after the main rendering and audio/input-independent
Stage240 timer, never inside the measured functions. The emulator
auditor reads the nine existing scripted gameplay screenshots, verifies
the old Stage238 and Stage241 evidence, and reports separate controls
for no-threat initial/hidden/cancelled/ended scenes.

C11, Clang and UBSan native controls test equal full images, alternating
samples, warm cache correctness, inactive controls, state invalidation,
invalid monotonic clocks, integer overflow and bounded telemetry writes.
A fail-closed screenshot decoder checks both time bars and readiness.

## Interpretation

The measured function covers CPU software terrain rasterization,
battle overlays and the optional threat-risk forecast; it does **not**
include framebuffer acquire, presentation, GPU, vsync, audio, controller
handling, host NeXium UI, the extra probe instrumentation itself, or
actual physical Nintendo Switch hardware.

The inactive-threat scenes are **negative controls** for ordinary
host/guest timing drift. Even if the cached render is faster when
threat prediction is active, it is not a measured FPS increase, a
whole-frame latency claim, a hardware benchmark or a port of the
original PS3 code. The A/B rendering overhead exists only in the
optional experiment NRO, not the default production build.
