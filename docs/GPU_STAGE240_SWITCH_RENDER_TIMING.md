# Stage240 — Switch guest software-render timing telemetry

Stage239 [PR #123](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/123)
measured the generated tactical forecast **on the GitHub Linux host**.
Both measurement artifacts showed ~302× less CPU wall time for the
cursor-invariant forecast function on one 8×6 simulation. That is NOT
a 302× game speedup, Switch CPU speedup, or frame-rate claim.

Stage240 prepares real **guest-side** render timing inside
`foj-isometric-research.nro` using the documented libnx
`armGetSystemTick()` and `armTicksToNs()` AArch64 counter API.
The timestamps surround **only**
`foj_iso_render_battle_cached_options`. They intentionally exclude
`framebufferBegin`, `framebufferEnd`, presentation, NeXium UI,
COLL overlays, controller polling and post-render HUD indicators.

`core/render_cost_meter.c` is portable C. It rejects invalid / zero
elapsed times, checks 64-bit accumulation overflow, and computes a
mean for each block of **32 valid renderer frames**. It reports the
latest completed block's mean, in **whole microseconds**, saturated at
65,535 µs rather than wrapping and claiming an unrealistically fast
render. Missing samples draw a distinct pending color.

The CPU renderer emits 16 low-bit-first values into small 3×8 pixel
stripes (one-pixel gap) starting at x=432, y=12 in the synthetic
1280×720 image. It does not occupy the Stage229 replay meter or
Stage238 cache audit. Compile-time assertions protect those positions.
Display is strictly diagnostic and does not read or change the
simulated combat state.

## Validation

- Strict C11/UBSan unit tests verify 32-sample mean, reset, overflow,
  saturation, pixel bit order, pending state and out-of-bounds failure.
- Nintendo Switch devkitA64/libnx builds check the actual timer calls.
- Previously established NeXium screenshots and game-behavior tests
  must still pass with the diagnostic enabled.

**Important:** A system-counter measurement from NeXium is an
*emulated guest timer*, not wall-clock FPS, native Nintendo Switch
hardware performance, GPU cost or end-to-end game latency. Guest
integration should only claim measured values after screenshots have
been collected and independently decoded; new diagnostic indicators
alone are not proof of performance.

No PS3 engine code, AI, encryption keys or original assets are used.
